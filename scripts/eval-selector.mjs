#!/usr/bin/env node

import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import {
  REVIEW_LENSES,
  selectReviewLenses,
} from '../plugins/review/skills/review-pr/select-review-lenses.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export const CODE_LENS_IDS = new Set([
  'ui-state-reactivity',
  'mutation-state-ownership',
  'authentication-authorization',
  'external-input-injection',
  'persistence-migration',
  'async-concurrency',
  'secrets-privacy-observability',
  'public-contracts-compatibility',
  'performance-resource-use',
]);

const ratio = (numerator, denominator) => (
  denominator === 0 ? 1 : numerator / denominator
);

export function percentile(values, fraction) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((left, right) => left - right);
  return sorted[Math.ceil(fraction * sorted.length) - 1];
}

export function median(values) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[middle - 1] + sorted[middle]) / 2
    : sorted[middle];
}

export function scoreSelector({ cases, policy, selector = selectReviewLenses }) {
  const lensIds = ['mandatory', ...REVIEW_LENSES.map(({ id }) => id)];
  const metrics = Object.fromEntries(lensIds.map((id) => [id, { tp: 0, fp: 0, fn: 0 }]));
  const perCase = [];
  let proseCodeLensCases = 0;
  let forbiddenLensViolations = 0;
  let tierEscalations = 0;

  for (const testCase of cases) {
    const expected = new Set(testCase.expectedLenses);
    const forbidden = new Set(testCase.forbiddenLenses);
    const selected = [...new Set(selector({
      paths: testCase.paths,
      diff: testCase.diff,
    }).map(({ id }) => id))];
    const selectedSet = new Set(selected);
    const forbiddenSelected = selected.filter((id) => forbidden.has(id));
    const codeLenses = selected.filter((id) => CODE_LENS_IDS.has(id));
    const codeLensCase = ['prose', 'config'].includes(testCase.kind) && codeLenses.length > 0;
    const nonMandatoryCount = selected.filter((id) => id !== 'mandatory').length;
    const tierEscalated = nonMandatoryCount >= 3;

    for (const id of lensIds) {
      if (selectedSet.has(id) && expected.has(id)) metrics[id].tp += 1;
      else if (selectedSet.has(id)) metrics[id].fp += 1;
      else if (expected.has(id)) metrics[id].fn += 1;
    }
    if (codeLensCase) proseCodeLensCases += 1;
    forbiddenLensViolations += forbiddenSelected.length;
    if (tierEscalated) tierEscalations += 1;
    perCase.push({
      id: testCase.id,
      selected,
      selectedCount: selected.length,
      forbiddenSelected,
      codeLenses,
      codeLensCase,
      tierEscalated,
    });
  }

  const perLens = Object.fromEntries(lensIds.map((id) => {
    const { tp, fp, fn } = metrics[id];
    const precision = ratio(tp, tp + fp);
    const recall = ratio(tp, tp + fn);
    return [id, {
      tp,
      fp,
      fn,
      precision,
      recall,
      f1: precision + recall === 0 ? 0 : 2 * precision * recall / (precision + recall),
    }];
  }));
  const selectedCounts = perCase.map(({ selectedCount }) => selectedCount);
  const selectorPolicy = policy.selector;
  const failedThresholds = [];
  const lowPrecisionLenses = Object.entries(perLens)
    .filter(([, metric]) => metric.precision < selectorPolicy.minLensPrecision)
    .map(([id]) => id);

  if (median(selectedCounts) > selectorPolicy.maxMedianLenses) {
    failedThresholds.push('maxMedianLenses');
  }
  if (lowPrecisionLenses.length > 0) failedThresholds.push('minLensPrecision');
  if (perLens.mandatory.recall < selectorPolicy.minMandatoryRecall) {
    failedThresholds.push('minMandatoryRecall');
  }
  if (proseCodeLensCases > selectorPolicy.maxProseCodeLensCases) {
    failedThresholds.push('maxProseCodeLensCases');
  }
  const tierEscalationRate = ratio(tierEscalations, cases.length);
  if (tierEscalationRate > selectorPolicy.maxTierEscalationRate) {
    failedThresholds.push('maxTierEscalationRate');
  }
  if (forbiddenLensViolations > 0) failedThresholds.push('forbiddenLenses');

  const violationCaseIds = perCase
    .filter(({ forbiddenSelected, codeLensCase, tierEscalated }) => (
      forbiddenSelected.length > 0 || codeLensCase || tierEscalated
    ))
    .map(({ id }) => id);

  return {
    passed: failedThresholds.length === 0,
    perLens,
    medianSelectedLenses: median(selectedCounts),
    p90SelectedLenses: percentile(selectedCounts, 0.9),
    proseCodeLensCases,
    forbiddenLensViolations,
    tierEscalationRate,
    lowPrecisionLenses,
    failedThresholds,
    violationCaseIds,
    perCase,
  };
}

export function formatSelectorReport(score) {
  const lines = [
    'Lens                         Precision  Recall  F1    TP  FP  FN',
    '---------------------------------------------------------------',
  ];
  for (const [id, metric] of Object.entries(score.perLens)) {
    lines.push(
      `${id.padEnd(28)} ${metric.precision.toFixed(2).padStart(9)}  ${metric.recall.toFixed(2).padStart(6)}  ${metric.f1.toFixed(2).padStart(4)}  ${String(metric.tp).padStart(2)}  ${String(metric.fp).padStart(2)}  ${String(metric.fn).padStart(2)}`,
    );
  }
  lines.push(
    '',
    `medianSelectedLenses: ${score.medianSelectedLenses}`,
    `p90SelectedLenses: ${score.p90SelectedLenses}`,
    `proseCodeLensCases: ${score.proseCodeLensCases}`,
    `forbiddenLensViolations: ${score.forbiddenLensViolations}`,
    `tierEscalationRate: ${score.tierEscalationRate.toFixed(2)}`,
    `failedThresholds: ${score.failedThresholds.join(', ') || 'none'}`,
    `violatingCaseIds: ${score.violationCaseIds.join(', ') || 'none'}`,
  );
  return lines.join('\n');
}

export function serializeSelectorScore(score, { json = false, enforced = true } = {}) {
  return json
    ? JSON.stringify({ ...score, enforced }, null, 2)
    : formatSelectorReport(score);
}

function parseArgs(argv) {
  if (argv.length === 0) return { json: false };
  if (argv.length === 1 && argv[0] === '--json') return { json: true };
  throw new Error(`unknown argument: ${argv.join(' ')}`);
}

function readJson(file) {
  return JSON.parse(readFileSync(file, 'utf8'));
}

export function runCli({
  argv = process.argv.slice(2),
  enforce = process.env.SELECTOR_METRICS_ENFORCE ?? '1',
  stdout = process.stdout,
  stderr = process.stderr,
} = {}) {
  const { json } = parseArgs(argv);
  const cases = readJson(path.join(ROOT, 'evals', 'selector', 'cases.json')).cases;
  const policy = readJson(path.join(ROOT, 'evals', 'policy.json'));
  const score = scoreSelector({ cases, policy });
  const enforced = enforce !== '0';
  const output = serializeSelectorScore(score, { json, enforced });

  stdout.write(`${output}\n`);
  if (!enforced) {
    stderr.write('NOT ENFORCED: SELECTOR_METRICS_ENFORCE=0\n');
    return 0;
  }
  return score.passed ? 0 : 1;
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    process.exitCode = runCli();
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 2;
  }
}
