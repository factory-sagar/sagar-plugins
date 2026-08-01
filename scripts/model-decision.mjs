#!/usr/bin/env node
// Apply evals/policy.json model-decision rules to fix-pair score output.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const COMPARISON_EPSILON = 1e-12;
const REQUIRED_ARGUMENTS = [
  'role',
  'incumbent',
  'challenger',
  'scores',
  'policy',
  'out',
];
const PRIVACY_PATTERNS = [
  { pattern: /\b[0-9a-f]{40}\b/i, label: 'a commit SHA' },
  { pattern: /factory-mono/i, label: 'a repository identity' },
  { pattern: /(?:\bPR[-\s#]*\d+\b|#\d+\b)/i, label: 'a PR number' },
  { pattern: /(?:^|[\s"])(?:\/|~\/|[A-Za-z]:[\\/])/, label: 'a repository path' },
];

export const MODEL_COST_MULTIPLIERS = Object.freeze({
  'claude-opus-5': 2,
  'claude-opus-5-fast': 4,
  'claude-opus-4-8': 2,
  'claude-sonnet-5': 1.2,
  'claude-haiku-4-5': 0.4,
  'gpt-5.6-sol': 2,
  'gpt-5.6-terra': 1,
  'gpt-5.6-luna': 0.4,
  'gpt-5.4-mini': 0.3,
  'glm-5.2': 0.55,
  'glm-5.2-fast': 1.1,
  'kimi-k3': 0.6,
  'kimi-k2.7-code': 0.4,
  'gemini-3.6-flash': 0.6,
});

function splitModelId(modelId) {
  const at = modelId.lastIndexOf('@');
  if (at <= 0 || at === modelId.length - 1) {
    throw new Error(`invalid model id ${JSON.stringify(modelId)}; expected model@effort`);
  }
  return { model: modelId.slice(0, at), effort: modelId.slice(at + 1) };
}

function modelCost(modelId, multipliers) {
  const { model } = splitModelId(modelId);
  const multiplier = multipliers[model];
  if (typeof multiplier !== 'number') {
    throw new Error(`unknown model ${JSON.stringify(model)}; add its Factory credit multiplier`);
  }
  return multiplier;
}

function assertCell(cell, label) {
  if (!cell || typeof cell !== 'object') {
    throw new Error(`${label} score cell is missing`);
  }
  for (const field of [
    'pairsScored',
    'pairHitRate',
    'runs',
    'creditsMedianPerRun',
    'durationMsMedianPerRun',
  ]) {
    if (typeof cell[field] !== 'number' || !Number.isFinite(cell[field]) || cell[field] < 0) {
      throw new Error(`${label} score cell has invalid ${field}`);
    }
  }
  if (typeof cell.modelId !== 'string') {
    throw new Error(`${label} score cell has invalid modelId`);
  }
}

function percentage(value) {
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * Decide whether a challenger should replace an incumbent from aggregate
 * fix-pair score cells. Both cells must include the corresponding modelId.
 */
export function decideModel({
  incumbent,
  challenger,
  policy,
  multipliers = MODEL_COST_MULTIPLIERS,
}) {
  assertCell(incumbent, 'incumbent');
  assertCell(challenger, 'challenger');
  const incumbentCost = modelCost(incumbent.modelId, multipliers);
  const challengerCost = modelCost(challenger.modelId, multipliers);

  if (!policy || typeof policy !== 'object') {
    throw new Error('modelDecision policy is missing');
  }
  for (const field of [
    'maxProcessRegression',
    'qualityGainForHigherCost',
    'costImprovementForQualityTie',
    'latencyImprovementForQualityTie',
  ]) {
    if (typeof policy[field] !== 'number' || !Number.isFinite(policy[field])) {
      throw new Error(`modelDecision policy has invalid ${field}`);
    }
  }

  if (incumbent.runs < 2 || challenger.runs < 2) {
    return {
      outcome: 'insufficient-data',
      rationale: 'Insufficient data: each model requires at least two runs.',
    };
  }
  if (incumbent.pairsScored < 3 || challenger.pairsScored < 3) {
    return {
      outcome: 'insufficient-data',
      rationale: 'Insufficient data: each model requires at least three scored pairs.',
    };
  }

  const qualityDelta = challenger.pairHitRate - incumbent.pairHitRate;
  if (-qualityDelta - policy.maxProcessRegression > COMPARISON_EPSILON) {
    return {
      outcome: 'keep',
      rationale: `Keep incumbent: challenger quality regressed by ${percentage(-qualityDelta)}.`,
    };
  }
  if (qualityDelta - policy.qualityGainForHigherCost >= -COMPARISON_EPSILON) {
    return {
      outcome: 'switch',
      rationale: `Switch: challenger quality gained ${percentage(qualityDelta)}.`,
    };
  }

  const costImprovement = (incumbentCost - challengerCost) / incumbentCost;
  if (costImprovement - policy.costImprovementForQualityTie >= -COMPARISON_EPSILON) {
    return {
      outcome: 'switch',
      rationale: `Switch: quality is a tie and challenger is ${percentage(costImprovement)} cheaper by Factory multiplier.`,
    };
  }
  const latencyImprovement =
    incumbent.durationMsMedianPerRun === 0
      ? 0
      : (incumbent.durationMsMedianPerRun - challenger.durationMsMedianPerRun) /
        incumbent.durationMsMedianPerRun;
  if (latencyImprovement - policy.latencyImprovementForQualityTie >= -COMPARISON_EPSILON) {
    return {
      outcome: 'switch',
      rationale: `Switch: quality is a tie and challenger is ${percentage(latencyImprovement)} faster.`,
    };
  }
  if (!policy.tiesKeepIncumbent) {
    return {
      outcome: 'switch',
      rationale: 'Switch: quality is a tie and policy does not keep the incumbent.',
    };
  }
  return {
    outcome: 'keep',
    rationale: 'Keep incumbent: quality is a tie and no efficiency threshold was met.',
  };
}

function roleModelField(role) {
  const parts = role.split(/[^a-zA-Z0-9]+/).filter(Boolean);
  if (parts.length === 0) throw new Error('role must contain letters or numbers');
  return `${parts.map((part, index) => index === 0 ? part.toLowerCase() : `${part[0].toUpperCase()}${part.slice(1)}`).join('')}Model`;
}

function dateFromId(id) {
  const date = id.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    throw new Error(`decision id ${JSON.stringify(id)} must begin with YYYY-MM-DD`);
  }
  return date;
}

export function assertPrivateRecord(record) {
  const serialized = JSON.stringify(record);
  for (const { pattern, label } of PRIVACY_PATTERNS) {
    if (pattern.test(serialized)) {
      throw new Error(`decision record violates privacy invariant: contains ${label}`);
    }
  }
}

export function buildDecisionRecord({ id, role, incumbent, challenger, decision }) {
  const chosen = decision.outcome === 'switch' ? challenger : incumbent;
  const { model, effort } = splitModelId(chosen.modelId);
  const record = {
    id,
    date: dateFromId(id),
    status: 'provisional',
    scope: [role],
    protocol: {
      tier: 'fix-pair-recall',
      fixture: `${Math.min(incumbent.pairsScored, challenger.pairsScored)} real-world fix-pair changes, human-verified corpus`,
      repetitions: Math.min(incumbent.runs, challenger.runs),
      networkAccess: true,
      artifacts: 'Fixtures, transcripts, repository identity, commit identifiers, and review metadata are not published.',
    },
    results: Object.fromEntries(
      [incumbent, challenger].map((cell) => [
        cell.modelId,
        {
          pairHitRate: cell.pairHitRate,
          pairsScored: cell.pairsScored,
          creditsMedianPerRun: cell.creditsMedianPerRun,
          durationMsMedianPerRun: cell.durationMsMedianPerRun,
        },
      ]),
    ),
    decision: {
      outcome: decision.outcome,
      [roleModelField(role)]: model,
      reasoningEffort: effort,
      rationale: decision.rationale,
    },
    limitations: [
      'Pilot-sized corpus; promotion to validated status requires repeated independent corpora.',
      'No identifying fixture or transcript data is committed.',
    ],
  };
  assertPrivateRecord(record);
  return record;
}

function parseArguments(argumentsList) {
  const parsed = { dryRun: false };
  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (argument === '--dry-run') {
      parsed.dryRun = true;
      continue;
    }
    if (!argument.startsWith('--')) {
      throw new Error(`unexpected argument ${JSON.stringify(argument)}`);
    }
    const key = argument.slice(2);
    const value = argumentsList[index + 1];
    if (!value || value.startsWith('--')) {
      throw new Error(`missing value for --${key}`);
    }
    if (key in parsed) throw new Error(`duplicate argument --${key}`);
    parsed[key] = value;
    index += 1;
  }
  for (const key of REQUIRED_ARGUMENTS) {
    if (!parsed[key]) throw new Error(`missing required argument --${key}`);
  }
  return parsed;
}

function readJson(file, label) {
  if (!existsSync(file)) throw new Error(`${label} file does not exist: ${file}`);
  try {
    return JSON.parse(readFileSync(file, 'utf8'));
  } catch (error) {
    throw new Error(`could not parse ${label} JSON: ${error.message}`);
  }
}

function outputId(outputFile) {
  const extension = path.extname(outputFile);
  if (extension !== '.json') {
    throw new Error('--out must name a .json decision record');
  }
  return path.basename(outputFile, extension);
}

function proposedAssignment(role, record) {
  const field = roleModelField(role);
  return [
    'PROPOSED model-assignment change (not applied):',
    `  role: ${role}`,
    `  model: ${record.decision[field]}@${record.decision.reasoningEffort}`,
    `  outcome: ${record.decision.outcome}`,
    '  apply manually in evals/model-assignments.json and matching droid frontmatter.',
  ].join('\n');
}

function main() {
  const args = parseArguments(process.argv.slice(2));
  const scores = readJson(args.scores, 'scores');
  const policyFile = readJson(args.policy, 'policy');
  const roleScores = scores?.roles?.[args.role];
  if (!roleScores?.models || typeof roleScores.models !== 'object') {
    throw new Error(`scores contain no model cells for role ${JSON.stringify(args.role)}`);
  }
  const incumbent = { ...roleScores.models[args.incumbent], modelId: args.incumbent };
  const challenger = { ...roleScores.models[args.challenger], modelId: args.challenger };
  const decision = decideModel({
    incumbent,
    challenger,
    policy: policyFile.modelDecision,
  });
  const record = buildDecisionRecord({
    id: outputId(args.out),
    role: args.role,
    incumbent,
    challenger,
    decision,
  });
  const serialized = `${JSON.stringify(record, null, 2)}\n`;

  console.log(proposedAssignment(args.role, record));
  console.log(serialized);
  if (!args.dryRun) {
    mkdirSync(path.dirname(args.out), { recursive: true });
    writeFileSync(args.out, serialized);
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  try {
    main();
  } catch (error) {
    console.error(`model-decision: ${error.message}`);
    process.exitCode = 2;
  }
}
