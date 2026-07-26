import assert from 'node:assert/strict';
import test from 'node:test';

import {
  median,
  percentile,
  scoreSelector,
  serializeSelectorScore,
} from './eval-selector.mjs';

const policy = {
  selector: {
    maxMedianLenses: 3,
    minLensPrecision: 0.8,
    minMandatoryRecall: 1,
    maxProseCodeLensCases: 0,
    maxTierEscalationRate: 0.5,
  },
};

const cases = [
  {
    id: 'prose-case',
    kind: 'prose',
    paths: ['docs/guide.md'],
    diff: 'guide',
    expectedLenses: ['mandatory'],
    forbiddenLenses: ['authentication-authorization'],
  },
  {
    id: 'code-case',
    kind: 'code',
    paths: ['src/View.tsx'],
    diff: 'component',
    expectedLenses: ['mandatory', 'ui-state-reactivity'],
    forbiddenLenses: [],
  },
  {
    id: 'config-case',
    kind: 'config',
    paths: ['package-lock.json'],
    diff: 'lockfile',
    expectedLenses: ['mandatory', 'dependencies-supply-chain'],
    forbiddenLenses: [],
  },
];

const selectByCase = (selectedByPath) => ({ paths }) => (
  selectedByPath[paths[0]].map((id) => ({ id }))
);

test('computes per-lens precision, recall, and F1', () => {
  const score = scoreSelector({
    cases,
    policy,
    selector: selectByCase({
      'docs/guide.md': ['mandatory', 'authentication-authorization'],
      'src/View.tsx': ['mandatory', 'ui-state-reactivity'],
      'package-lock.json': ['mandatory', 'dependencies-supply-chain'],
    }),
  });

  assert.deepEqual(score.perLens.mandatory, {
    tp: 3, fp: 0, fn: 0, precision: 1, recall: 1, f1: 1,
  });
  assert.deepEqual(score.perLens['ui-state-reactivity'], {
    tp: 1, fp: 0, fn: 0, precision: 1, recall: 1, f1: 1,
  });
  assert.deepEqual(score.perLens['authentication-authorization'], {
    tp: 0, fp: 1, fn: 0, precision: 0, recall: 1, f1: 0,
  });
});

test('uses nearest-rank p90 and average median', () => {
  assert.equal(median([1, 2, 3, 4]), 2.5);
  assert.equal(percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9), 9);
});

test('detects forbidden lenses and code lenses on prose', () => {
  const score = scoreSelector({
    cases,
    policy,
    selector: selectByCase({
      'docs/guide.md': ['mandatory', 'authentication-authorization'],
      'src/View.tsx': ['mandatory', 'ui-state-reactivity'],
      'package-lock.json': ['mandatory', 'dependencies-supply-chain'],
    }),
  });

  assert.equal(score.forbiddenLensViolations, 1);
  assert.equal(score.proseCodeLensCases, 1);
  assert.deepEqual(score.perCase[0].forbiddenSelected, ['authentication-authorization']);
  assert.equal(score.perCase[0].codeLensCase, true);
});

test('passes thresholds for an exact selector', () => {
  const score = scoreSelector({
    cases,
    policy,
    selector: selectByCase({
      'docs/guide.md': ['mandatory'],
      'src/View.tsx': ['mandatory', 'ui-state-reactivity'],
      'package-lock.json': ['mandatory', 'dependencies-supply-chain'],
    }),
  });

  assert.equal(score.passed, true);
  assert.equal(score.medianSelectedLenses, 2);
  assert.equal(score.p90SelectedLenses, 2);
  assert.equal(score.tierEscalationRate, 0);
  assert.deepEqual(score.failedThresholds, []);
});

test('fails threshold paths and records tier escalation', () => {
  const score = scoreSelector({
    cases,
    policy,
    selector: selectByCase({
      'docs/guide.md': ['mandatory', 'authentication-authorization', 'async-concurrency', 'persistence-migration'],
      'src/View.tsx': ['mandatory'],
      'package-lock.json': ['mandatory'],
    }),
  });

  assert.equal(score.passed, false);
  assert.equal(score.tierEscalationRate, 1 / 3);
  assert.deepEqual(score.failedThresholds, [
    'minLensPrecision',
    'maxProseCodeLensCases',
    'forbiddenLenses',
  ]);
  assert.deepEqual(score.violationCaseIds, ['prose-case']);
});

test('serializes the machine-readable score shape', () => {
  const score = scoreSelector({
    cases,
    policy,
    selector: selectByCase({
      'docs/guide.md': ['mandatory'],
      'src/View.tsx': ['mandatory', 'ui-state-reactivity'],
      'package-lock.json': ['mandatory', 'dependencies-supply-chain'],
    }),
  });
  const json = JSON.parse(serializeSelectorScore(score, { json: true, enforced: false }));

  assert.equal(json.enforced, false);
  assert.equal(json.passed, true);
  assert.equal(json.perLens.mandatory.precision, 1);
  assert.equal(json.perCase.length, 3);
});
