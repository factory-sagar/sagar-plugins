import test from 'node:test';
import assert from 'node:assert/strict';

import { compareBaseline } from './compare-baseline.mjs';

const baseline = {
  task: '10-review-pr-tier-selection',
  taskVersion: 1,
  judgeVersion: 1,
  judgeModel: 'claude-opus-4-8',
  contractSha: 'abc',
  execModel: 'gpt-5.6-sol',
  passRate: 1,
  failCount: 0,
};

const candidate = (overrides = {}) => ({
  taskVersion: 1,
  judgeVersion: 1,
  judgeModel: 'claude-opus-4-8',
  contractSha: 'abc',
  execModel: 'gpt-5.6-sol',
  judge: { verdict: 'pass' },
  ...overrides,
});

test('matching green candidates are not a regression', () => {
  const result = compareBaseline({
    baseline,
    candidates: [candidate(), candidate(), candidate()],
  });
  assert.equal(result.comparable, true);
  assert.equal(result.regression, false);
  assert.equal(result.candidatePassRate, 1);
});

test('a pass-rate drop below the baseline is a regression', () => {
  const result = compareBaseline({
    baseline,
    candidates: [candidate(), candidate({ judge: { verdict: 'partial' } })],
  });
  assert.equal(result.regression, true);
  assert.equal(result.passRateRegression, true);
});

test('a new fail against a zero-fail baseline is a regression', () => {
  const result = compareBaseline({
    baseline: { ...baseline, passRate: 0.5 },
    candidates: [
      candidate({ judge: { verdict: 'pass' } }),
      candidate({ judge: { verdict: 'fail' } }),
    ],
  });
  assert.equal(result.newFailure, true);
  assert.equal(result.regression, true);
});

test('a task, judge, or contract version change is not comparable', () => {
  for (const overrides of [
    { taskVersion: 2 },
    { judgeVersion: 2 },
    { judgeModel: 'other-judge' },
    { contractSha: 'def' },
  ]) {
    const result = compareBaseline({
      baseline,
      candidates: [candidate(overrides)],
    });
    assert.equal(result.comparable, false, JSON.stringify(overrides));
    assert.equal(result.incomparable.length, 1);
  }
});

test('an exec-model change stays comparable but is reported', () => {
  const result = compareBaseline({
    baseline,
    candidates: [candidate({ execModel: 'glm-5.2', judge: { verdict: 'pass' } })],
  });
  assert.equal(result.comparable, true);
  assert.equal(result.modelChanged, true);
  assert.equal(result.regression, false);
});
