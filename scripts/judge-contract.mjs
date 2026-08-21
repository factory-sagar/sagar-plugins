#!/usr/bin/env node
// The single ingestion seam for judged golden-task verdicts (JUDGE.md Version 2).
//
//   node scripts/judge-contract.mjs --task <task-file> --verdict-md <verdict.md> --out <verdict.json>
//
// The judge grades two axes and the harness owns the verdict: this module parses the
// task's Intent / Fulfillment / Boundaries axes, extracts the judge's JSON block,
// validates axis coverage and field shapes, recomputes the derived verdict
// (wrong-target or violated boundary -> fail; intent missed -> fail; partially
// achieved -> partial; achieved -> pass), and refuses any judgment whose verdict
// disagrees with its own axes. On success it writes the stamped verdict envelope
// consumed by scripts/accept-baseline.sh and scripts/compare-baseline.mjs, whose
// shapes are unchanged from schemaVersion 1.
//
// Env for the envelope (stamped by scripts/run-golden-task.sh): TASK_NAME,
// TASK_VERSION, JUDGE_VERSION, JUDGE_MODEL, JUDGE_EFFORT, EXEC_MODEL, EXEC_EFFORT,
// CONTRACT_SOURCE, CONTRACT_SHA, STARTED_AT, FINISHED_AT.
//
// Exit codes: 0 valid verdict written; 1 contract violation (nothing written); 2 usage.
//
// Dependency-free by design, matching scripts/validate.mjs.

import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const INTENT_ASSESSMENTS = ['achieved', 'partially achieved', 'missed'];
const FULFILLMENT_STATUSES = ['met', 'partially met', 'unmet'];

// Section extraction mirrors scripts/validate-evals.mjs: a section runs from its
// "## " heading to the next one; bullets are "- " lines with indented continuations.
function sectionLines(lines, heading) {
  const headingIndex = lines.indexOf(heading);
  if (headingIndex === -1) return null;
  const body = [];
  for (let i = headingIndex + 1; i < lines.length; i++) {
    if (/^## /.test(lines[i])) break;
    body.push(lines[i]);
  }
  return body;
}

function sectionBullets(lines, heading) {
  const body = sectionLines(lines, heading);
  if (body === null) return [];
  const bullets = [];
  for (const line of body) {
    if (/^- /.test(line)) bullets.push(line.slice(2).trim());
    else if (bullets.length > 0 && /^\s+\S/.test(line)) {
      bullets[bullets.length - 1] += ` ${line.trim()}`;
    }
  }
  return bullets;
}

export function parseTaskAxes(markdown) {
  const lines = markdown.split('\n');
  const intentBody = sectionLines(lines, '## Intent');
  const intent = intentBody === null ? null : intentBody.join('\n').trim() || null;
  return {
    intent,
    fulfillment: sectionBullets(lines, '## Fulfillment'),
    boundaries: sectionBullets(lines, '## Boundaries'),
  };
}

export function extractJudgeJson(text) {
  const fenced = [...text.matchAll(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/g)];
  let candidate = fenced.length > 0 ? fenced[fenced.length - 1][1] : null;
  if (candidate === null) {
    // No fence: take the outermost object that ends at the final closing brace.
    const end = text.lastIndexOf('}');
    if (end === -1) return null;
    let depth = 0;
    let start = -1;
    for (let i = end; i >= 0; i--) {
      if (text[i] === '}') depth += 1;
      else if (text[i] === '{') {
        depth -= 1;
        if (depth === 0) { start = i; break; }
      }
    }
    if (start === -1) return null;
    candidate = text.slice(start, end + 1);
  }
  try {
    const parsed = JSON.parse(candidate);
    return typeof parsed === 'object' && parsed !== null ? parsed : null;
  } catch {
    return null;
  }
}

export function deriveVerdict(judge) {
  if (judge?.target?.matched === false) return 'fail';
  if ((Array.isArray(judge?.boundaries) ? judge.boundaries : []).some((b) => b?.violated === true)) {
    return 'fail';
  }
  const assessment = judge?.intent?.assessment;
  if (assessment === 'missed') return 'fail';
  if (assessment === 'partially achieved') return 'partial';
  if (assessment === 'achieved') return 'pass';
  return null;
}

const isNonEmptyString = (value) => typeof value === 'string' && value.trim() !== '';

export function validateJudgeRecord(judge, axes) {
  const errors = [];
  if (typeof judge !== 'object' || judge === null) {
    return ['judgment is not a JSON object'];
  }

  if (typeof judge.target?.matched !== 'boolean') {
    errors.push('target.matched must be a boolean');
  } else if (!isNonEmptyString(judge.target.evidence)) {
    errors.push('target.evidence must be a non-empty string');
  }

  const assessment = judge.intent?.assessment;
  if (!INTENT_ASSESSMENTS.includes(assessment)) {
    errors.push(`intent.assessment ${JSON.stringify(assessment)} is not ${INTENT_ASSESSMENTS.join(' | ')}`);
  } else if (!isNonEmptyString(judge.intent.rationale)) {
    errors.push('intent.rationale must be a non-empty string');
  }

  const fulfillment = Array.isArray(judge.fulfillment) ? judge.fulfillment : [];
  if (!Array.isArray(judge.fulfillment)) {
    errors.push('fulfillment must be an array');
  } else if (fulfillment.length !== axes.fulfillment.length) {
    errors.push(`fulfillment covers ${fulfillment.length} of ${axes.fulfillment.length} task criteria — every criterion is judged exactly once`);
  }
  let statusesValid = fulfillment.length > 0;
  fulfillment.forEach((entry, index) => {
    if (!isNonEmptyString(entry?.criterion)) errors.push(`fulfillment[${index}].criterion must be a non-empty string`);
    if (!FULFILLMENT_STATUSES.includes(entry?.status)) {
      statusesValid = false;
      errors.push(`fulfillment[${index}].status ${JSON.stringify(entry?.status)} is not ${FULFILLMENT_STATUSES.join(' | ')}`);
    }
    if (!isNonEmptyString(entry?.evidence)) errors.push(`fulfillment[${index}].evidence must be a non-empty string ('none' when absent)`);
  });

  const boundaries = Array.isArray(judge.boundaries) ? judge.boundaries : [];
  if (!Array.isArray(judge.boundaries)) {
    errors.push('boundaries must be an array');
  } else if (boundaries.length !== axes.boundaries.length) {
    errors.push(`boundaries covers ${boundaries.length} of ${axes.boundaries.length} task boundaries — every boundary is judged exactly once`);
  }
  boundaries.forEach((entry, index) => {
    if (!isNonEmptyString(entry?.boundary)) errors.push(`boundaries[${index}].boundary must be a non-empty string`);
    if (typeof entry?.violated !== 'boolean') errors.push(`boundaries[${index}].violated must be a boolean`);
    if (!isNonEmptyString(entry?.evidence)) errors.push(`boundaries[${index}].evidence must be a non-empty string ('none' when absent)`);
  });

  // Coherence guards: the intent axis interprets the criteria, it does not override
  // them. Checked only when coverage and statuses are themselves valid.
  if (statusesValid && fulfillment.length === axes.fulfillment.length && INTENT_ASSESSMENTS.includes(assessment)) {
    if (assessment === 'missed' && fulfillment.every((entry) => entry.status === 'met')) {
      errors.push('intent "missed" is incoherent: every fulfillment criterion is met — encode the failure as an unmet criterion or a violated boundary');
    }
    if (assessment === 'achieved' && fulfillment.every((entry) => entry.status === 'unmet')) {
      errors.push('intent "achieved" is incoherent: every fulfillment criterion is unmet');
    }
  }

  const derived = deriveVerdict(judge);
  if (derived !== null && judge.verdict !== derived) {
    errors.push(`verdict ${JSON.stringify(judge.verdict)} != derived ${JSON.stringify(derived)} — the verdict is computed from target, boundaries, and intent, never judged directly`);
  }

  return errors;
}

function argValue(argv, flag) {
  const index = argv.indexOf(flag);
  return index === -1 ? null : argv[index + 1] ?? null;
}

function main() {
  const argv = process.argv.slice(2);
  const taskFile = argValue(argv, '--task');
  const verdictMd = argValue(argv, '--verdict-md');
  const out = argValue(argv, '--out');
  if (!taskFile || !verdictMd || !out) {
    console.error('usage: judge-contract.mjs --task <task-file> --verdict-md <verdict.md> --out <verdict.json>');
    process.exit(2);
  }

  const axes = parseTaskAxes(readFileSync(taskFile, 'utf8'));
  const axisProblems = [];
  if (axes.intent === null) axisProblems.push('missing "## Intent" prose');
  if (axes.fulfillment.length === 0) axisProblems.push('no "## Fulfillment" criteria');
  if (axes.boundaries.length === 0) axisProblems.push('no "## Boundaries" entries');
  if (axisProblems.length > 0) {
    console.error(`judge-contract: task file lacks v2 axes: ${axisProblems.join(', ')} (${taskFile})`);
    process.exit(1);
  }

  const judge = extractJudgeJson(readFileSync(verdictMd, 'utf8'));
  if (judge === null) {
    console.error('judge-contract: could not parse a judge verdict JSON block from the judge output');
    process.exit(1);
  }
  const errors = validateJudgeRecord(judge, axes);
  if (errors.length > 0) {
    for (const error of errors) console.error(`judge-contract: ${error}`);
    process.exit(1);
  }

  const env = process.env;
  const envelope = {
    schemaVersion: 1,
    task: env.TASK_NAME,
    taskVersion: Number(env.TASK_VERSION),
    judgeVersion: env.JUDGE_VERSION ? Number(env.JUDGE_VERSION) : null,
    judgeModel: env.JUDGE_MODEL,
    judgeReasoningEffort: env.JUDGE_EFFORT,
    execModel: env.EXEC_MODEL || null,
    execReasoningEffort: env.EXEC_EFFORT || null,
    contractSource: env.CONTRACT_SOURCE || null,
    contractSha: env.CONTRACT_SHA || null,
    startedAt: env.STARTED_AT,
    finishedAt: env.FINISHED_AT,
    judge,
  };
  writeFileSync(out, `${JSON.stringify(envelope, null, 2)}\n`);
  console.log(`verdict: ${judge.verdict} -> ${out}`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main();
}
