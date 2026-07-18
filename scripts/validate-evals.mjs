#!/usr/bin/env node
// Structural invariant validator for the committed eval definitions.
//
//   node scripts/validate-evals.mjs                       # full validation
//   node scripts/validate-evals.mjs --require-bumps REF   # + require golden-task
//                                                         #   Version bumps vs git REF
//
// Guards the harness contracts that scripts/run-golden-task.sh,
// scripts/eval-routing.mjs, and scripts/compare-baseline.mjs depend on:
// golden-task section shape, Version lines, and target resolution (replicating
// the runner's extraction exactly), the routing case schema, policy thresholds,
// the model-assignment registry's referential integrity, and accepted verdict
// baselines. Generated output under evals/runs/ and evals/results/ is not
// validated here because it is not versioned.
//
// Dependency-free by design, matching scripts/validate.mjs.

import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EVALS = path.join(ROOT, 'evals');
const errors = [];
const warnings = [];
const fail = (file, msg) => errors.push(`${path.relative(ROOT, file)}: ${msg}`);
const warn = (file, msg) => warnings.push(`${path.relative(ROOT, file)}: ${msg}`);

const read = (f) => readFileSync(f, 'utf8');
const readJson = (f) => {
  try { return JSON.parse(read(f)); }
  catch (e) { fail(f, `invalid JSON: ${e.message}`); return null; }
};

const WORKFLOWS = new Set(['spec', 'implement', 'review-pr', 'ship']);
const droidNames = new Set();
const skillNames = new Set();
const pluginsDir = path.join(ROOT, 'plugins');
for (const plugin of readdirSync(pluginsDir)) {
  if (plugin.startsWith('.')) continue;
  const droidsDir = path.join(pluginsDir, plugin, 'droids');
  if (existsSync(droidsDir)) {
    for (const f of readdirSync(droidsDir)) {
      if (f.endsWith('.md')) droidNames.add(path.basename(f, '.md'));
    }
  }
  const skillsDir = path.join(pluginsDir, plugin, 'skills');
  if (existsSync(skillsDir)) {
    for (const s of readdirSync(skillsDir)) {
      if (existsSync(path.join(skillsDir, s, 'SKILL.md'))) skillNames.add(s);
    }
  }
}

// ---------- 1. golden tasks ----------
// Section extraction mirrors scripts/run-golden-task.sh: the target is the first
// whitespace token of the first non-empty line after "## Target" with backticks
// and periods removed; a section's block is the first fence after its heading.
function extractTargetName(lines) {
  const headingIndex = lines.indexOf('## Target');
  if (headingIndex === -1) return null;
  for (let i = headingIndex + 1; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === '') continue;
    return line.replaceAll('`', '').replaceAll('.', '').split(' ')[0] || null;
  }
  return null;
}

function extractFencedBlock(lines, heading) {
  const headingIndex = lines.indexOf(heading);
  if (headingIndex === -1) return null;
  let inBlock = false;
  const block = [];
  for (let i = headingIndex + 1; i < lines.length; i++) {
    if (/^```/.test(lines[i])) {
      if (inBlock) return block.join('\n');
      inBlock = true;
      continue;
    }
    if (inBlock) block.push(lines[i]);
  }
  return inBlock ? block.join('\n') : null;
}

function sectionBullets(lines, heading) {
  const headingIndex = lines.indexOf(heading);
  if (headingIndex === -1) return null;
  const bullets = [];
  for (let i = headingIndex + 1; i < lines.length; i++) {
    if (/^## /.test(lines[i])) break;
    if (/^- /.test(lines[i])) bullets.push(lines[i]);
  }
  return bullets;
}

const tasksDir = path.join(EVALS, 'golden-tasks');
const taskFiles = readdirSync(tasksDir)
  .filter((f) => /^\d{2}-.+\.md$/.test(f))
  .sort()
  .map((f) => path.join(tasksDir, f));
if (taskFiles.length === 0) fail(tasksDir, 'no golden task files found');

const tasksReadme = path.join(tasksDir, 'README.md');
const tasksReadmeText = existsSync(tasksReadme) ? read(tasksReadme) : '';
if (!tasksReadmeText) fail(tasksReadme, 'missing golden-tasks README.md');

const taskTargets = new Map();
for (const file of taskFiles) {
  const lines = read(file).split('\n');
  if (!lines.some((line) => /^Version: \d+$/.test(line))) {
    fail(file, 'no "Version: N" line — baselines are only comparable at a pinned task version');
  }
  const target = extractTargetName(lines);
  if (!target) {
    fail(file, 'no resolvable "## Target" line');
  } else if (!droidNames.has(target) && !skillNames.has(target)) {
    fail(file, `target "${target}" is not a droid or skill on disk`);
  } else {
    taskTargets.set(path.basename(file, '.md'), target);
  }
  const prompt = extractFencedBlock(lines, '## Prompt');
  if (prompt === null) fail(file, 'no fenced block after "## Prompt"');
  else if (!prompt.trim()) fail(file, '"## Prompt" block is empty');
  if (lines.includes('## Setup')) {
    const setup = extractFencedBlock(lines, '## Setup');
    if (setup === null || !setup.trim()) fail(file, '"## Setup" heading present but its fenced block is missing or empty');
  }
  for (const heading of ['## Must pass', '## Must not do']) {
    const bullets = sectionBullets(lines, heading);
    if (bullets === null) fail(file, `missing "${heading}" section`);
    else if (bullets.length === 0) fail(file, `"${heading}" has no "- " assertions`);
  }
  const score = sectionBullets(lines, '## Score');
  if (score === null) fail(file, 'missing "## Score" section');
  else {
    const scoreText = score.join('\n');
    for (const verdict of ['pass', 'fail']) {
      if (!scoreText.includes(`\`${verdict}\``)) fail(file, `"## Score" does not define \`${verdict}\``);
    }
  }
  const stem = path.basename(file);
  if (tasksReadmeText && !tasksReadmeText.includes(`(./${stem})`)) {
    fail(tasksReadme, `task ${stem} is not listed in the README table`);
  }
}
for (const [, link] of tasksReadmeText.matchAll(/\]\(\.\/(\d{2}-[^)]+\.md)\)/g)) {
  if (!existsSync(path.join(tasksDir, link))) {
    fail(tasksReadme, `README links ./${link} but the task file does not exist`);
  }
}

// ---------- 2. judge contract ----------
const judgeFile = path.join(tasksDir, 'JUDGE.md');
if (!existsSync(judgeFile)) fail(judgeFile, 'missing JUDGE.md');
else {
  const judge = read(judgeFile);
  for (const field of ['"verdict"', '"must_pass"', '"must_not_do"']) {
    if (!judge.includes(field)) fail(judgeFile, `judge output contract is missing the ${field} field`);
  }
  if (!/^Version: \d+$/m.test(judge)) {
    fail(judgeFile, 'no "Version: N" line — verdicts are only comparable at a pinned judge version');
  }
}

// ---------- 3. routing cases ----------
const casesFile = path.join(EVALS, 'routing', 'cases.json');
const casesDoc = existsSync(casesFile) ? readJson(casesFile) : (fail(casesFile, 'missing routing cases'), null);
if (casesDoc) {
  if (casesDoc.schemaVersion !== 1) fail(casesFile, `schemaVersion ${casesDoc.schemaVersion} != 1`);
  const cases = Array.isArray(casesDoc.cases) ? casesDoc.cases : [];
  if (cases.length === 0) fail(casesFile, 'no routing cases');
  const seen = new Set();
  for (const c of cases) {
    const id = c.id ?? '<missing id>';
    if (seen.has(id)) fail(casesFile, `duplicate case id "${id}"`);
    seen.add(id);
    if (typeof c.prompt !== 'string' || !c.prompt.trim()) fail(casesFile, `case "${id}" has no prompt`);
    if (c.expectedPrimary !== null && !WORKFLOWS.has(c.expectedPrimary)) {
      fail(casesFile, `case "${id}" expectedPrimary "${c.expectedPrimary}" is not a public workflow or null`);
    }
    if ('expectedSequence' in c) {
      if (!Array.isArray(c.expectedSequence) || c.expectedSequence.length === 0) {
        fail(casesFile, `case "${id}" expectedSequence must be a nonempty array`);
      } else {
        for (const step of c.expectedSequence) {
          if (!WORKFLOWS.has(step)) fail(casesFile, `case "${id}" expectedSequence step "${step}" is not a public workflow`);
        }
        if (c.expectedSequence[0] !== c.expectedPrimary) {
          fail(casesFile, `case "${id}" expectedSequence[0] "${c.expectedSequence[0]}" != expectedPrimary "${c.expectedPrimary}"`);
        }
      }
    }
    if ('critical' in c && typeof c.critical !== 'boolean') fail(casesFile, `case "${id}" critical must be boolean`);
  }
}

// ---------- 4. policy thresholds ----------
const policyFile = path.join(EVALS, 'policy.json');
const policy = existsSync(policyFile) ? readJson(policyFile) : (fail(policyFile, 'missing policy.json'), null);
if (policy) {
  if (policy.schemaVersion !== 1) fail(policyFile, `schemaVersion ${policy.schemaVersion} != 1`);
  const inUnit = (v) => typeof v === 'number' && v >= 0 && v <= 1;
  const routing = policy.routing ?? {};
  if (!inUnit(routing.criticalRecall) || routing.criticalRecall === 0) fail(policyFile, 'routing.criticalRecall must be in (0, 1]');
  if (!inUnit(routing.criticalPrecision) || routing.criticalPrecision === 0) fail(policyFile, 'routing.criticalPrecision must be in (0, 1]');
  if (!Number.isInteger(routing.maxExtraInvocationsPerCase) || routing.maxExtraInvocationsPerCase < 0) {
    fail(policyFile, 'routing.maxExtraInvocationsPerCase must be an integer >= 0');
  }
  if (!inUnit(routing.negativeFalseInvocationRate)) fail(policyFile, 'routing.negativeFalseInvocationRate must be in [0, 1]');
  const repetitions = policy.repetitions ?? {};
  for (const key of ['promptChange', 'modelChange']) {
    if (!Number.isInteger(repetitions[key]) || repetitions[key] < 1) fail(policyFile, `repetitions.${key} must be an integer >= 1`);
  }
  for (const section of ['quality', 'modelDecision']) {
    if (typeof policy[section] !== 'object' || policy[section] === null) fail(policyFile, `missing "${section}" section`);
  }
}

// ---------- 5. model-assignment registry integrity ----------
const assignmentsFile = path.join(EVALS, 'model-assignments.json');
const assignmentsDoc = existsSync(assignmentsFile)
  ? readJson(assignmentsFile)
  : (fail(assignmentsFile, 'missing model-assignments.json'), null);
if (assignmentsDoc) {
  if (assignmentsDoc.schemaVersion !== 1) fail(assignmentsFile, `schemaVersion ${assignmentsDoc.schemaVersion} != 1`);
  const assignments = assignmentsDoc.assignments ?? {};
  for (const [name, entry] of Object.entries(assignments)) {
    if (!droidNames.has(name)) fail(assignmentsFile, `assignment "${name}" has no droid file on disk`);
    if (typeof entry.model !== 'string' || !entry.model) fail(assignmentsFile, `assignment "${name}" missing model`);
    if (typeof entry.reasoningEffort !== 'string' || !entry.reasoningEffort) fail(assignmentsFile, `assignment "${name}" missing reasoningEffort`);
    if (!['provisional', 'validated'].includes(entry.status)) {
      fail(assignmentsFile, `assignment "${name}" status "${entry.status}" must be provisional or validated`);
    }
    for (const evidence of entry.evidence ?? []) {
      if (!existsSync(path.join(EVALS, 'model-decisions', `${evidence}.json`))) {
        fail(assignmentsFile, `assignment "${name}" evidence "${evidence}" has no evals/model-decisions/${evidence}.json`);
      }
    }
  }
  for (const name of droidNames) {
    if (!(name in assignments)) fail(assignmentsFile, `droid "${name}" has no model assignment entry`);
  }
}

// ---------- 6. model decisions ----------
const decisionsDir = path.join(EVALS, 'model-decisions');
if (existsSync(decisionsDir)) {
  for (const f of readdirSync(decisionsDir).filter((f) => f.endsWith('.json'))) {
    const file = path.join(decisionsDir, f);
    const decision = readJson(file);
    if (!decision) continue;
    if (decision.id !== path.basename(f, '.json')) fail(file, `id "${decision.id}" != filename stem`);
    for (const field of ['date', 'status']) {
      if (!decision[field]) fail(file, `missing "${field}"`);
    }
  }
}

// ---------- 7. harness scripts referenced by the docs exist ----------
for (const script of [
  'run-golden-task.sh',
  'eval-routing.mjs',
  'eval-routing.test.mjs',
  'accept-baseline.sh',
  'compare-baseline.mjs',
]) {
  const file = path.join(ROOT, 'scripts', script);
  if (!existsSync(file)) fail(file, 'harness script is missing');
}

// ---------- 8. accepted verdict baselines ----------
const baselinesDir = path.join(EVALS, 'baselines');
if (existsSync(baselinesDir)) {
  for (const f of readdirSync(baselinesDir).filter((f) => f.endsWith('.json'))) {
    const file = path.join(baselinesDir, f);
    const baseline = readJson(file);
    if (!baseline) continue;
    if (baseline.schemaVersion !== 1) fail(file, `schemaVersion ${baseline.schemaVersion} != 1`);
    const stem = path.basename(f, '.json');
    if (baseline.task !== stem) fail(file, `task "${baseline.task}" != filename stem "${stem}"`);
    if (!existsSync(path.join(tasksDir, `${stem}.md`))) fail(file, `no golden task file for baseline "${stem}"`);
    if (!Number.isInteger(baseline.taskVersion)) fail(file, 'taskVersion must be an integer');
    if (typeof baseline.passRate !== 'number' || baseline.passRate < 0 || baseline.passRate > 1) {
      fail(file, 'passRate must be in [0, 1]');
    }
    if (!Number.isInteger(baseline.failCount) || baseline.failCount < 0) fail(file, 'failCount must be an integer >= 0');
    if (!Array.isArray(baseline.runs) || baseline.runs.length === 0) {
      fail(file, 'runs must be a nonempty array');
      continue;
    }
    for (const run of baseline.runs) {
      if (!['pass', 'partial', 'fail'].includes(run.verdict)) {
        fail(file, `run verdict "${run.verdict}" must be pass, partial, or fail`);
      }
      if (!run.transcript || !existsSync(path.join(baselinesDir, run.transcript))) {
        fail(file, `accepted transcript missing: ${run.transcript}`);
      }
    }
  }
}

// ---------- 9. golden-task Version bumps vs a base ref ----------
const bumpIdx = process.argv.indexOf('--require-bumps');
if (bumpIdx !== -1) {
  const baseRef = process.argv[bumpIdx + 1];
  if (!baseRef) { console.error('--require-bumps requires a git ref'); process.exit(2); }
  const git = (...args) =>
    execFileSync('git', args, { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
  const gitShow = (ref, p) => {
    try { return git('show', `${ref}:${p}`); } catch { return null; }
  };
  const changed = [...new Set([
    ...git('diff', '--name-only', `${baseRef}...HEAD`).split('\n'),
    ...git('diff', '--name-only').split('\n'),
    ...git('diff', '--name-only', '--cached').split('\n'),
  ].filter(Boolean))];
  for (const f of changed.filter((f) => /^evals\/golden-tasks\/\d{2}-.+\.md$/.test(f))) {
    const before = gitShow(baseRef, f);
    const currentPath = path.join(ROOT, f);
    if (before === null || !existsSync(currentPath)) continue; // new or deleted task
    const vBefore = before.match(/^Version: (\d+)$/m)?.[1] ?? null;
    const vAfter = read(currentPath).match(/^Version: (\d+)$/m)?.[1] ?? null;
    if (vBefore !== null && vBefore === vAfter) {
      fail(currentPath, `golden task changed vs ${baseRef} but Version was not bumped — existing baselines would silently stop being comparable`);
    }
  }
}

// ---------- report ----------
for (const w of warnings) console.log(`WARN  ${w}`);
for (const e of errors) console.log(`ERROR ${e}`);
console.log(`\n${taskFiles.length} golden tasks, ${taskTargets.size} resolved targets — ${errors.length} error(s), ${warnings.length} warning(s)`);
process.exit(errors.length > 0 ? 1 : 0);
