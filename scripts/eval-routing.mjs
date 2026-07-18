#!/usr/bin/env node

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const ratio = (numerator, denominator) => (
  denominator === 0 ? 1 : numerator / denominator
);

export function scoreRouting({ cases, results, policy }) {
  const resultByCase = new Map();
  for (const result of results) {
    if (resultByCase.has(result.caseId)) {
      throw new Error(`duplicate routing result: ${result.caseId}`);
    }
    resultByCase.set(result.caseId, result);
  }

  const perCase = [];
  let positiveCases = 0;
  let routedCases = 0;
  let correctPrimary = 0;
  let negativeCases = 0;
  let negativeFalseInvocations = 0;
  let extraInvocations = 0;

  for (const testCase of cases) {
    const result = resultByCase.get(testCase.id);
    if (!result) throw new Error(`missing routing result: ${testCase.id}`);
    const selected = Array.isArray(result.selected) ? result.selected : [];
    const expectedSequence = Array.isArray(testCase.expectedSequence)
      ? testCase.expectedSequence
      : testCase.expectedPrimary === null
        ? []
        : [testCase.expectedPrimary];
    const expected = expectedSequence[0] ?? null;
    const primary = selected[0] ?? null;
    const primaryCorrect = primary === expected;
    const correct = (
      selected.length === expectedSequence.length
      && selected.every((name, index) => name === expectedSequence[index])
    );
    const extras = Math.max(0, selected.length - expectedSequence.length);

    if (expected === null) {
      negativeCases += 1;
      if (selected.length > 0) negativeFalseInvocations += 1;
    } else {
      positiveCases += 1;
      if (selected.length > 0) routedCases += 1;
      if (primaryCorrect) correctPrimary += 1;
    }
    extraInvocations += extras;
    perCase.push({
      id: testCase.id,
      critical: Boolean(testCase.critical),
      expectedPrimary: expected,
      expectedSequence,
      selected,
      correct,
      extraInvocations: extras,
    });
  }

  const recall = ratio(correctPrimary, positiveCases);
  const precision = ratio(correctPrimary, routedCases + negativeFalseInvocations);
  const negativeFalseInvocationRate = negativeCases === 0
    ? 0
    : negativeFalseInvocations / negativeCases;
  const routingPolicy = policy.routing;
  const criticalCasesPass = perCase
    .filter(({ critical }) => critical)
    .every(({ correct }) => correct);
  const invocationBudgetPass = perCase.every(
    ({ extraInvocations: extras }) => (
      extras <= routingPolicy.maxExtraInvocationsPerCase
    ),
  );
  const passed = (
    criticalCasesPass
    && invocationBudgetPass
    && recall >= routingPolicy.criticalRecall
    && precision >= routingPolicy.criticalPrecision
    && negativeFalseInvocationRate <= routingPolicy.negativeFalseInvocationRate
  );

  return {
    passed,
    recall,
    precision,
    negativeFalseInvocationRate,
    extraInvocations,
    invocationBudgetPass,
    perCase,
  };
}

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (!['--cases', '--results', '--policy'].includes(arg)) {
      throw new Error(`unknown argument: ${arg}`);
    }
    options[arg.slice(2)] = argv[++index];
  }
  for (const required of ['cases', 'results', 'policy']) {
    if (!options[required]) throw new Error(`missing --${required}`);
  }
  return options;
}

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const casesFile = readJson(options.cases);
  const resultsFile = readJson(options.results);
  const policy = readJson(options.policy);
  const score = scoreRouting({
    cases: casesFile.cases,
    results: resultsFile.results,
    policy,
  });
  process.stdout.write(`${JSON.stringify(score, null, 2)}\n`);
  process.exitCode = score.passed ? 0 : 1;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 2;
  }
}
