#!/usr/bin/env node
// Gate judged golden-task runs against an accepted verdict baseline.
//
//   node scripts/compare-baseline.mjs <task-name> <verdict.json> [<verdict.json>...]
//
// Exit codes:
//   0  no regression
//   1  regression: candidate pass rate below the baseline pass rate, or a new
//      `fail` verdict when the baseline had none
//   2  usage or missing files
//   3  not comparable: task version, judge version, judge model, or contract
//      hash differs from the baseline — that is a re-baseline, not a comparison
//
// A differing exec model is compared (that is the model-A/B use case) but
// reported, so evals/policy.json modelDecision rules can be applied to the
// output.

import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SCORE = { pass: 1, partial: 0.5, fail: 0 };
const IDENTITY_FIELDS = ['taskVersion', 'judgeVersion', 'judgeModel', 'contractSha'];

export function compareBaseline({ baseline, candidates }) {
  const incomparable = [];
  for (const candidate of candidates) {
    for (const field of IDENTITY_FIELDS) {
      if (candidate[field] !== baseline[field]) {
        incomparable.push(
          `${candidate.sourceFile ?? 'candidate'}: ${field} ${JSON.stringify(candidate[field])} != baseline ${JSON.stringify(baseline[field])}`,
        );
      }
    }
  }
  if (incomparable.length > 0) {
    return { comparable: false, incomparable };
  }
  const outcomes = candidates.map((candidate) => candidate.judge.verdict);
  const passRate = outcomes.reduce((sum, outcome) => sum + SCORE[outcome], 0) / outcomes.length;
  const newFailure = baseline.failCount === 0 && outcomes.includes('fail');
  const passRateRegression = passRate < baseline.passRate;
  const modelChanged = candidates.some(
    (candidate) => candidate.execModel !== baseline.execModel,
  );
  return {
    comparable: true,
    regression: passRateRegression || newFailure,
    passRateRegression,
    newFailure,
    modelChanged,
    baselinePassRate: baseline.passRate,
    candidatePassRate: passRate,
    outcomes,
  };
}

function main() {
  const [taskName, ...verdictFiles] = process.argv.slice(2);
  if (!taskName || verdictFiles.length === 0) {
    console.error('usage: compare-baseline.mjs <task-name> <verdict.json>...');
    process.exit(2);
  }
  const baselineFile = path.join(ROOT, 'evals', 'baselines', `${taskName}.json`);
  if (!existsSync(baselineFile)) {
    console.error(`no accepted baseline: ${path.relative(ROOT, baselineFile)} — run scripts/accept-baseline.sh first`);
    process.exit(2);
  }
  const baseline = JSON.parse(readFileSync(baselineFile, 'utf8'));
  const candidates = verdictFiles.map((file) => {
    if (!existsSync(file)) {
      console.error(`missing verdict file: ${file}`);
      process.exit(2);
    }
    return { ...JSON.parse(readFileSync(file, 'utf8')), sourceFile: file };
  });
  const result = compareBaseline({ baseline, candidates });
  if (!result.comparable) {
    for (const reason of result.incomparable) console.error(`NOT COMPARABLE  ${reason}`);
    console.error('re-baseline with scripts/accept-baseline.sh instead of comparing');
    process.exit(3);
  }
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.regression ? 1 : 0);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main();
}
