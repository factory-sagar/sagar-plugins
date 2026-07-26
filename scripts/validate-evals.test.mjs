import assert from 'node:assert/strict';
import test from 'node:test';

import { staleBaselineErrors } from './validate-evals.mjs';

const contract = 'plugins/review/skills/review-pr/SKILL.md';
const task = { task: '10-review-pr-tier-selection', contractSource: contract };
const baseline = (overrides = {}) => ({
  task: task.task,
  contractSource: contract,
  contractSha: 'a'.repeat(64),
  judgeVersion: 1,
  ...overrides,
});

test('passes when a changed contract matches its baseline hash', () => {
  const errors = staleBaselineErrors({
    tasks: [task],
    changedFiles: new Set([contract]),
    baselines: { [task.task]: baseline() },
    currentHashes: { [contract]: 'a'.repeat(64) },
    judgeVersion: 1,
  });

  assert.deepEqual(errors, []);
});

test('fails a changed contract whose baseline hash differs', () => {
  const errors = staleBaselineErrors({
    tasks: [task],
    changedFiles: new Set([contract]),
    baselines: { [task.task]: baseline() },
    currentHashes: { [contract]: 'b'.repeat(64) },
    judgeVersion: 1,
  });

  assert.match(errors[0], /current hash b{12} != baseline hash a{12}/);
  assert.match(errors[0], /scripts\/accept-baseline\.sh evals\/golden-tasks\/10-review-pr-tier-selection\.md/);
});

test('fails a changed contract with no accepted baseline', () => {
  const errors = staleBaselineErrors({
    tasks: [task],
    changedFiles: new Set([contract]),
    baselines: {},
    currentHashes: { [contract]: 'a'.repeat(64) },
    judgeVersion: 1,
  });

  assert.match(errors[0], /has no accepted baseline/);
  assert.match(errors[0], /targets changed contract "plugins\/review\/skills\/review-pr\/SKILL\.md"/);
});

test('does not gate a stale hash when its contract is unchanged', () => {
  const errors = staleBaselineErrors({
    tasks: [task],
    changedFiles: new Set(),
    baselines: { [task.task]: baseline() },
    currentHashes: { [contract]: 'b'.repeat(64) },
    judgeVersion: 1,
  });

  assert.deepEqual(errors, []);
});

test('fails when a baseline contract source no longer exists', () => {
  const errors = staleBaselineErrors({
    tasks: [],
    changedFiles: new Set(),
    baselines: { [task.task]: baseline({ contractSource: 'plugins/removed/SKILL.md' }) },
    currentHashes: {},
    judgeVersion: 1,
  });

  assert.match(errors[0], /contractSource "plugins\/removed\/SKILL\.md" no longer exists/);
  assert.match(errors[0], /remove or retarget the baseline/);
});

test('gates judge version drift only after JUDGE.md changes', () => {
  const options = {
    tasks: [],
    baselines: { [task.task]: baseline({ judgeVersion: 1 }) },
    currentHashes: { [contract]: 'a'.repeat(64) },
    judgeVersion: 2,
  };

  assert.deepEqual(staleBaselineErrors({ ...options, changedFiles: new Set() }), []);
  const errors = staleBaselineErrors({
    ...options,
    changedFiles: new Set(['evals/golden-tasks/JUDGE.md']),
  });
  assert.match(errors[0], /judgeVersion 1 != current JUDGE\.md Version 2 after JUDGE\.md changed/);
});
