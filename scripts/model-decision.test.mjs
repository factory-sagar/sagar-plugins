import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  MODEL_COST_MULTIPLIERS,
  assertPrivateRecord,
  buildDecisionRecord,
  decideModel,
} from './model-decision.mjs';

const POLICY = {
  tiesKeepIncumbent: true,
  maxProcessRegression: 0.02,
  maxFalsePositiveRegression: 0.01,
  qualityGainForHigherCost: 0.05,
  costImprovementForQualityTie: 0.3,
  latencyImprovementForQualityTie: 0.4,
};

function cell(modelId, overrides = {}) {
  return {
    modelId,
    pairsScored: 4,
    pairHits: 3,
    pairHitRate: 0.75,
    nearMisses: 0,
    outsideRegions: 0,
    findingsTotal: 3,
    runs: 2,
    erroredRuns: 0,
    creditsTotal: 4,
    creditsMedianPerRun: 2,
    durationMsMedianPerRun: 1_000,
    ...overrides,
  };
}

function decision(incumbentOverrides, challengerOverrides) {
  return decideModel({
    incumbent: cell('gpt-5.6-sol@xhigh', incumbentOverrides),
    challenger: cell('claude-opus-5@high', challengerOverrides),
    policy: POLICY,
    multipliers: MODEL_COST_MULTIPLIERS,
  });
}

test('switches when the challenger gains the required quality margin', () => {
  const result = decision(
    { pairHitRate: 0.3 },
    { pairHitRate: 0.35, creditsMedianPerRun: 999, durationMsMedianPerRun: 999_999 },
  );

  assert.equal(result.outcome, 'switch');
  assert.match(result.rationale, /quality gain/i);
});

test('keeps the incumbent at the exact permitted quality regression boundary', () => {
  const result = decision({ pairHitRate: 0.35 }, { pairHitRate: 0.33 });

  assert.equal(result.outcome, 'keep');
  assert.match(result.rationale, /tie/i);
});

test('keeps the incumbent on a quality tie when policy keeps ties', () => {
  const result = decision({ pairHitRate: 0.75 }, { pairHitRate: 0.77 });

  assert.equal(result.outcome, 'keep');
  assert.match(result.rationale, /tie/i);
});

test('switches a quality tie when the challenger is sufficiently cheaper', () => {
  const result = decideModel({
    incumbent: cell('gpt-5.6-sol@xhigh', { pairHitRate: 0.75 }),
    challenger: cell('gpt-5.6-terra@high', { pairHitRate: 0.76 }),
    policy: POLICY,
    multipliers: MODEL_COST_MULTIPLIERS,
  });

  assert.equal(result.outcome, 'switch');
  assert.match(result.rationale, /cheaper/i);
});

test('switches a quality tie when the challenger is sufficiently faster', () => {
  const result = decision(
    { pairHitRate: 0.75, durationMsMedianPerRun: 2_000 },
    { pairHitRate: 0.76, durationMsMedianPerRun: 1_000 },
  );

  assert.equal(result.outcome, 'switch');
  assert.match(result.rationale, /faster/i);
});

test('rejects a challenger with quality regression beyond the policy limit', () => {
  const result = decision({ pairHitRate: 0.8 }, { pairHitRate: 0.77 });

  assert.equal(result.outcome, 'keep');
  assert.match(result.rationale, /regressed/i);
});

test('reports insufficient data when either model has fewer than two runs', () => {
  const result = decision({}, { runs: 1 });

  assert.equal(result.outcome, 'insufficient-data');
  assert.match(result.rationale, /runs/i);
});

test('reports insufficient data when either model has fewer than three scored pairs', () => {
  const result = decision({ pairsScored: 2 }, {});

  assert.equal(result.outcome, 'insufficient-data');
  assert.match(result.rationale, /pairs/i);
});

test('fails clearly for an unknown model', () => {
  assert.throws(
    () =>
      decideModel({
        incumbent: cell('unknown-model@high'),
        challenger: cell('claude-opus-5@high'),
        policy: POLICY,
        multipliers: MODEL_COST_MULTIPLIERS,
      }),
    /unknown model.*unknown-model/i,
  );
});

test('projects only scrubbed metrics into the decision record', () => {
  const incumbent = cell('gpt-5.6-sol@xhigh', { pairHitRate: 0.75 });
  const challenger = cell('claude-opus-5@high', { pairHitRate: 0.8 });
  const record = buildDecisionRecord({
    id: '2026-07-30-change-review-claude-opus-5-high',
    role: 'change-review',
    incumbent,
    challenger,
    decision: decideModel({ incumbent, challenger, policy: POLICY }),
  });
  const serialized = JSON.stringify({
    ...record,
    ignoredSourceData: {
      sha: '0123456789abcdef0123456789abcdef01234567',
      repository: 'factory-mono',
      pullRequest: 123,
      findingTitle: 'The title must not be copied',
      path: '/Users/dev/workspace/plugins/evals/results/fixpairs/scores.json',
    },
  });

  assert.equal(record.protocol.fixture, '4 real-world fix-pair changes, human-verified corpus');
  assert.equal(record.decision.changeReviewModel, 'claude-opus-5');
  assert.equal(record.decision.reasoningEffort, 'high');
  assert.doesNotMatch(JSON.stringify(record), /[0-9a-f]{40}/i);
  assert.doesNotMatch(JSON.stringify(record), /factory-mono/i);
  assert.doesNotMatch(JSON.stringify(record), /PR\s*#?\d+|#\d+/i);
  assert.doesNotMatch(JSON.stringify(record), /The title must not be copied/);
  assert.doesNotMatch(JSON.stringify(record), /\/Users\/sagar\//);
  assert.match(serialized, /factory-mono/);
});

test('rejects bare PR-number references from a record', () => {
  assert.throws(
    () => assertPrivateRecord({ id: '2026-07-30-change-review-#123' }),
    /privacy invariant.*PR number/i,
  );
});

test('dry-run prints a proposed assignment and record without writing it', () => {
  const directory = mkdtempSync(path.join(tmpdir(), 'model-decision-'));
  try {
    const scoresFile = path.join(directory, 'scores.json');
    const policyFile = path.join(directory, 'policy.json');
    const outputFile = path.join(
      directory,
      '2026-07-30-change-review-claude-opus-5-high.json',
    );
    writeFileSync(
      scoresFile,
      JSON.stringify({
        schemaVersion: 1,
        roles: {
          'change-review': {
            models: {
              'gpt-5.6-sol@xhigh': cell('gpt-5.6-sol@xhigh'),
              'claude-opus-5@high': cell('claude-opus-5@high', { pairHitRate: 0.8 }),
            },
            perPair: [
              {
                commit: '0123456789abcdef0123456789abcdef01234567',
                repository: 'factory-mono',
                findingTitle: 'Private finding',
              },
            ],
          },
        },
      }),
    );
    writeFileSync(policyFile, JSON.stringify({ modelDecision: POLICY }));

    const result = spawnSync(
      process.execPath,
      [
        'scripts/model-decision.mjs',
        '--role',
        'change-review',
        '--incumbent',
        'gpt-5.6-sol@xhigh',
        '--challenger',
        'claude-opus-5@high',
        '--scores',
        scoresFile,
        '--policy',
        policyFile,
        '--out',
        outputFile,
        '--dry-run',
      ],
      {
        cwd: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..'),
        encoding: 'utf8',
      },
    );

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /PROPOSED model-assignment change/i);
    assert.match(result.stdout, /"changeReviewModel": "claude-opus-5"/);
    assert.match(result.stdout, /"id": "2026-07-30-change-review-claude-opus-5-high"/);
    assert.equal(result.stdout.includes('factory-mono'), false);
    assert.equal(result.stdout.includes('Private finding'), false);
    assert.equal(result.stdout.includes('0123456789abcdef0123456789abcdef01234567'), false);
    assert.equal(existsSync(outputFile), false);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
