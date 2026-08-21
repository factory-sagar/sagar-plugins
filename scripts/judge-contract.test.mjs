import assert from 'node:assert/strict';
import test from 'node:test';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  deriveVerdict,
  extractJudgeJson,
  parseTaskAxes,
  validateJudgeRecord,
} from './judge-contract.mjs';

const TASK_MD = `# Golden Task 99: Example

Version: 2

## Target

\`change-review\`.

## Intent

The run exists to catch the seeded boundary defect in the diff and ground the finding in
standards evidence rather than style preference.

## Prompt

\`\`\`text
Review this diff.
\`\`\`

## Fulfillment

- Flags the unchecked cast as a material boundary issue.
- Grounds the finding in loaded standards topics.

## Boundaries

- Runs tests or package commands.
- Suggests implementation patches inline.

## Score

- Derived, not judged: any wrong-target run or violated boundary → \`fail\`; intent \`missed\` → \`fail\`.
- Intent \`partially achieved\` with no violation → \`partial\`.
- Intent \`achieved\` with no violation → \`pass\`.
`;

const validJudge = (overrides = {}) => ({
  task: '99-example',
  target: { matched: true, evidence: 'transcript reads the change-review contract and reviews inline' },
  intent: { assessment: 'achieved', rationale: 'found the seeded defect and tied it to standards' },
  fulfillment: [
    { criterion: 'flags the unchecked cast', status: 'met', evidence: 'JSON.parse(rawJson) as SavedFilter flagged' },
    { criterion: 'grounds finding in standards', status: 'met', evidence: 'BOUNDARIES_AND_PARSING cited' },
  ],
  boundaries: [
    { boundary: 'runs tests or package commands', violated: false, evidence: 'none' },
    { boundary: 'suggests inline patches', violated: false, evidence: 'none' },
  ],
  verdict: 'pass',
  ...overrides,
});

test('parseTaskAxes extracts intent prose, fulfillment criteria, and boundaries', () => {
  const axes = parseTaskAxes(TASK_MD);
  assert.match(axes.intent, /seeded boundary defect/);
  assert.equal(axes.fulfillment.length, 2);
  assert.match(axes.fulfillment[1], /standards topics/);
  assert.equal(axes.boundaries.length, 2);
  assert.match(axes.boundaries[0], /tests or package commands/);
});

test('parseTaskAxes returns null intent and empty axes when sections are absent', () => {
  const axes = parseTaskAxes('# Task\n\nVersion: 1\n\n## Prompt\n\n```text\nx\n```\n');
  assert.equal(axes.intent, null);
  assert.deepEqual(axes.fulfillment, []);
  assert.deepEqual(axes.boundaries, []);
});

test('extractJudgeJson takes the last fenced JSON block', () => {
  const text = 'preamble\n```json\n{"verdict":"fail"}\n```\nmore\n```json\n{"verdict":"pass"}\n```\n';
  assert.deepEqual(extractJudgeJson(text), { verdict: 'pass' });
});

test('extractJudgeJson falls back to a trailing brace-balanced object', () => {
  const text = `judgment follows\n${JSON.stringify(validJudge(), null, 2)}\n`;
  assert.equal(extractJudgeJson(text).verdict, 'pass');
});

test('extractJudgeJson returns null when no JSON object parses', () => {
  assert.equal(extractJudgeJson('no json here'), null);
  assert.equal(extractJudgeJson('{"unterminated": true'), null);
});

test('deriveVerdict fails a wrong-target run regardless of the axes', () => {
  const judge = validJudge({ target: { matched: false, evidence: 'a different skill handled it' } });
  assert.equal(deriveVerdict(judge), 'fail');
});

test('deriveVerdict fails any boundary violation even with intent achieved', () => {
  const judge = validJudge();
  judge.boundaries[0] = { ...judge.boundaries[0], violated: true, evidence: 'ran pnpm test' };
  assert.equal(deriveVerdict(judge), 'fail');
});

test('deriveVerdict maps intent grades to fail, partial, and pass', () => {
  assert.equal(deriveVerdict(validJudge({ intent: { assessment: 'missed', rationale: 'r' } })), 'fail');
  assert.equal(deriveVerdict(validJudge({ intent: { assessment: 'partially achieved', rationale: 'r' } })), 'partial');
  assert.equal(deriveVerdict(validJudge()), 'pass');
});

test('a complete, coherent record validates cleanly', () => {
  assert.deepEqual(validateJudgeRecord(validJudge(), parseTaskAxes(TASK_MD)), []);
});

test('fulfillment coverage must match the task criteria one to one', () => {
  const judge = validJudge();
  judge.fulfillment = judge.fulfillment.slice(0, 1);
  const errors = validateJudgeRecord(judge, parseTaskAxes(TASK_MD));
  assert.equal(errors.length, 1);
  assert.match(errors[0], /fulfillment covers 1 of 2 task criteria/);
});

test('boundary coverage must match the task boundaries one to one', () => {
  const judge = validJudge();
  judge.boundaries = [...judge.boundaries, { boundary: 'invented', violated: false, evidence: 'none' }];
  const errors = validateJudgeRecord(judge, parseTaskAxes(TASK_MD));
  assert.equal(errors.length, 1);
  assert.match(errors[0], /boundaries covers 3 of 2 task boundaries/);
});

test('unsupported statuses and missing fields are rejected', () => {
  const judge = validJudge();
  judge.fulfillment[0] = { ...judge.fulfillment[0], status: 'mostly' };
  judge.boundaries[1] = { boundary: 'suggests inline patches', violated: 'no', evidence: 'none' };
  delete judge.target;
  const errors = validateJudgeRecord(judge, parseTaskAxes(TASK_MD));
  assert.ok(errors.some((e) => /fulfillment\[0\]\.status "mostly"/.test(e)));
  assert.ok(errors.some((e) => /boundaries\[1\]\.violated must be a boolean/.test(e)));
  assert.ok(errors.some((e) => /target\.matched must be a boolean/.test(e)));
});

test('intent assessment outside the enum is rejected', () => {
  const errors = validateJudgeRecord(
    validJudge({ intent: { assessment: 'heroic', rationale: 'r' } }),
    parseTaskAxes(TASK_MD),
  );
  assert.ok(errors.some((e) => /intent\.assessment "heroic"/.test(e)));
});

test('a verdict inconsistent with its axes is rejected', () => {
  const errors = validateJudgeRecord(
    validJudge({ verdict: 'partial' }),
    parseTaskAxes(TASK_MD),
  );
  assert.equal(errors.length, 1);
  assert.match(errors[0], /verdict "partial" != derived "pass"/);
});

test('intent cannot be missed when every criterion is met', () => {
  const judge = validJudge({ intent: { assessment: 'missed', rationale: 'r' }, verdict: 'fail' });
  const errors = validateJudgeRecord(judge, parseTaskAxes(TASK_MD));
  assert.equal(errors.length, 1);
  assert.match(errors[0], /intent "missed" is incoherent: every fulfillment criterion is met/);
});

test('intent cannot be achieved when every criterion is unmet', () => {
  const judge = validJudge();
  judge.fulfillment = judge.fulfillment.map((entry) => ({ ...entry, status: 'unmet', evidence: 'none' }));
  const errors = validateJudgeRecord(judge, parseTaskAxes(TASK_MD));
  assert.equal(errors.length, 1);
  assert.match(errors[0], /intent "achieved" is incoherent: every fulfillment criterion is unmet/);
});

test('anti-conflation: an unmet criterion with intent achieved stays valid but derives pass', () => {
  const judge = validJudge();
  judge.fulfillment[1] = { ...judge.fulfillment[1], status: 'partially met' };
  assert.deepEqual(validateJudgeRecord(judge, parseTaskAxes(TASK_MD)), []);
});

// CLI: the runner's single ingestion seam. It must write a stamped envelope on valid
// input and exit nonzero (writing nothing) on contract violations.
const HERE = path.dirname(fileURLToPath(import.meta.url));
const CLI = path.join(HERE, 'judge-contract.mjs');

const cliEnv = {
  ...process.env,
  TASK_NAME: '99-example',
  TASK_VERSION: '2',
  JUDGE_VERSION: '2',
  JUDGE_MODEL: 'claude-opus-4-8',
  JUDGE_EFFORT: 'xhigh',
  EXEC_MODEL: 'kimi-k3',
  EXEC_EFFORT: 'max',
  CONTRACT_SOURCE: 'plugins/review/droids/change-review.md',
  CONTRACT_SHA: 'a'.repeat(64),
  STARTED_AT: '2026-08-21T00:00:00Z',
  FINISHED_AT: '2026-08-21T00:05:00Z',
};

test('CLI writes a stamped verdict envelope for a valid judgment', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'judge-contract-'));
  const taskFile = path.join(dir, '99-example.md');
  const verdictMd = path.join(dir, 'verdict.md');
  const out = path.join(dir, 'verdict.json');
  writeFileSync(taskFile, TASK_MD);
  writeFileSync(verdictMd, `\`\`\`json\n${JSON.stringify(validJudge(), null, 2)}\n\`\`\`\n`);
  execFileSync(process.execPath, [CLI, '--task', taskFile, '--verdict-md', verdictMd, '--out', out], { env: cliEnv });
  const envelope = JSON.parse(readFileSync(out, 'utf8'));
  assert.equal(envelope.schemaVersion, 1);
  assert.equal(envelope.task, '99-example');
  assert.equal(envelope.taskVersion, 2);
  assert.equal(envelope.judgeVersion, 2);
  assert.equal(envelope.judgeModel, 'claude-opus-4-8');
  assert.equal(envelope.contractSha, 'a'.repeat(64));
  assert.equal(envelope.judge.verdict, 'pass');
  assert.equal(envelope.judge.intent.assessment, 'achieved');
});

test('CLI exits nonzero on a contract violation and writes nothing', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'judge-contract-'));
  const taskFile = path.join(dir, '99-example.md');
  const verdictMd = path.join(dir, 'verdict.md');
  const out = path.join(dir, 'verdict.json');
  writeFileSync(taskFile, TASK_MD);
  writeFileSync(verdictMd, `\`\`\`json\n${JSON.stringify(validJudge({ verdict: 'partial' }))}\n\`\`\`\n`);
  assert.throws(() => {
    execFileSync(process.execPath, [CLI, '--task', taskFile, '--verdict-md', verdictMd, '--out', out], {
      env: cliEnv,
      stdio: 'pipe',
    });
  }, /Command failed|judge-contract/);
  assert.throws(() => readFileSync(out, 'utf8'));
});
