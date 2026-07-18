import assert from 'node:assert/strict';
import test from 'node:test';

import { scoreRouting } from './eval-routing.mjs';

const policy = {
  routing: {
    criticalRecall: 0.95,
    criticalPrecision: 0.98,
    maxExtraInvocationsPerCase: 2,
    negativeFalseInvocationRate: 0.02,
  },
};

const cases = [
  { id: 'review', critical: true, expectedPrimary: 'review-pr' },
  { id: 'plan', critical: true, expectedPrimary: 'spec' },
  { id: 'negative', critical: true, expectedPrimary: null },
];

test('passes exact primary routing without extra invocations', () => {
  const score = scoreRouting({
    cases,
    results: [
      { caseId: 'review', selected: ['review-pr'] },
      { caseId: 'plan', selected: ['spec'] },
      { caseId: 'negative', selected: [] },
    ],
    policy,
  });

  assert.equal(score.passed, true);
  assert.equal(score.recall, 1);
  assert.equal(score.precision, 1);
  assert.equal(score.negativeFalseInvocationRate, 0);
  assert.equal(score.extraInvocations, 0);
});

test('fails wrong, missing, and false-positive routing', () => {
  const score = scoreRouting({
    cases,
    results: [
      { caseId: 'review', selected: ['review-fix', 'review-pr'] },
      { caseId: 'plan', selected: [] },
      { caseId: 'negative', selected: ['ship'] },
    ],
    policy,
  });

  assert.equal(score.passed, false);
  assert.equal(score.recall, 0);
  assert.equal(score.precision, 0);
  assert.equal(score.negativeFalseInvocationRate, 1);
  assert.equal(score.extraInvocations, 2);
});

test('fails redundant workflow invocation even when the primary route is correct', () => {
  const score = scoreRouting({
    cases: cases.map((testCase) => (
      testCase.id === 'review' ? { ...testCase, critical: false } : testCase
    )),
    results: [
      { caseId: 'review', selected: ['review-pr', 'ship'] },
      { caseId: 'plan', selected: ['spec'] },
      { caseId: 'negative', selected: [] },
    ],
    policy: {
      routing: {
        ...policy.routing,
        maxExtraInvocationsPerCase: 0,
      },
    },
  });

  assert.equal(score.recall, 1);
  assert.equal(score.precision, 1);
  assert.equal(score.passed, false);
});

test('accepts an explicitly expected multi-stage workflow sequence', () => {
  const score = scoreRouting({
    cases: [
      {
        id: 'implement-ship',
        critical: true,
        expectedPrimary: 'implement',
        expectedSequence: ['implement', 'ship'],
      },
    ],
    results: [
      { caseId: 'implement-ship', selected: ['implement', 'ship'] },
    ],
    policy,
  });

  assert.equal(score.passed, true);
  assert.equal(score.extraInvocations, 0);
});

test('rejects missing and duplicate result records', () => {
  assert.throws(
    () => scoreRouting({
      cases,
      results: [{ caseId: 'review', selected: ['review-pr'] }],
      policy,
    }),
    /missing routing result/,
  );
  assert.throws(
    () => scoreRouting({
      cases: [cases[0]],
      results: [
        { caseId: 'review', selected: ['review-pr'] },
        { caseId: 'review', selected: ['review-pr'] },
      ],
      policy,
    }),
    /duplicate routing result/,
  );
});
