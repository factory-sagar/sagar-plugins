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

import { REVIEW_LENSES } from '../plugins/review/skills/review-pr/select-review-lenses.mjs';

const MIN_SELECTOR_CASES = 50;
const MIN_CASES_PER_LENS = 3;
const MIN_PROSE_CONFIG_CASES = 12;
const MIN_REAL_PROVENANCE_SHARE = 0.6;

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
// Coverage floor: warn (not fail) on droids no golden task exercises, so expensive-failure
// droids cannot silently drop out of the regression net.
const coveredTargets = new Set(taskTargets.values());
for (const name of [...droidNames].sort()) {
  if (!coveredTargets.has(name)) {
    warn(tasksDir, `droid "${name}" has no golden task exercising it`);
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
    if (!['hook', 'model'].includes(c.layer)) {
      fail(casesFile, `case "${id}" layer "${c.layer}" must be "hook" (CI parity test) or "model" (live eval only)`);
    }
  }
}

// ---------- 4. selector cases ----------
const selectorCasesFile = path.join(EVALS, 'selector', 'cases.json');
const selectorCasesDoc = existsSync(selectorCasesFile)
  ? readJson(selectorCasesFile)
  : (fail(selectorCasesFile, 'missing selector cases'), null);
if (selectorCasesDoc) {
  if (selectorCasesDoc.schemaVersion !== 1) fail(selectorCasesFile, `schemaVersion ${selectorCasesDoc.schemaVersion} != 1`);
  if (!Number.isInteger(selectorCasesDoc.version) || selectorCasesDoc.version < 1) {
    fail(selectorCasesFile, 'version must be an integer >= 1');
  }
  const cases = Array.isArray(selectorCasesDoc.cases) ? selectorCasesDoc.cases : [];
  // Corpus size and balance are invariants, not preferences: per-lens precision and recall
  // are only meaningful with several labeled cases per lens, and prose/config cases are the
  // ones that expose keyword contamination.
  if (cases.length < MIN_SELECTOR_CASES) {
    fail(selectorCasesFile, `expected at least ${MIN_SELECTOR_CASES} cases, found ${cases.length}`);
  }
  const seen = new Set();
  for (const c of cases) {
    const id = c.id ?? '<missing id>';
    if (seen.has(id)) fail(selectorCasesFile, `duplicate case id "${id}"`);
    seen.add(id);
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) fail(selectorCasesFile, `case "${id}" id must be kebab-case`);
    if (typeof c.provenance !== 'string' || !c.provenance.trim()) fail(selectorCasesFile, `case "${id}" missing provenance`);
    if (!['code', 'prose', 'config'].includes(c.kind)) fail(selectorCasesFile, `case "${id}" has invalid kind`);
    if (!Array.isArray(c.paths) || c.paths.length === 0 || c.paths.some((p) => typeof p !== 'string' || !p)) {
      fail(selectorCasesFile, `case "${id}" paths must be a nonempty string array`);
    }
    if (typeof c.diff !== 'string' || !c.diff.trim()) fail(selectorCasesFile, `case "${id}" missing diff`);
    for (const field of ['expectedLenses', 'forbiddenLenses']) {
      if (!Array.isArray(c[field]) || c[field].some((lens) => typeof lens !== 'string' || !lens)) {
        fail(selectorCasesFile, `case "${id}" ${field} must be a string array`);
      }
    }
    if (c.expectedLenses?.[0] !== 'mandatory') fail(selectorCasesFile, `case "${id}" expectedLenses must begin with mandatory`);
    if (c.forbiddenLenses?.some((lens) => c.expectedLenses?.includes(lens))) {
      fail(selectorCasesFile, `case "${id}" has a lens both expected and forbidden`);
    }
    if (typeof c.note !== 'string' || !c.note.trim()) fail(selectorCasesFile, `case "${id}" missing note`);
  }
  const expectedCounts = new Map();
  for (const c of cases) {
    for (const lens of c.expectedLenses ?? []) {
      expectedCounts.set(lens, (expectedCounts.get(lens) ?? 0) + 1);
    }
  }
  for (const { id } of REVIEW_LENSES) {
    const count = expectedCounts.get(id) ?? 0;
    if (count < MIN_CASES_PER_LENS) {
      fail(selectorCasesFile, `lens "${id}" is expected in only ${count} cases; need ${MIN_CASES_PER_LENS} for a measurable recall`);
    }
  }
  const proseOrConfig = cases.filter((c) => c.kind === 'prose' || c.kind === 'config').length;
  if (proseOrConfig < MIN_PROSE_CONFIG_CASES) {
    fail(selectorCasesFile, `only ${proseOrConfig} prose/config cases; need ${MIN_PROSE_CONFIG_CASES} to measure keyword contamination`);
  }
  const real = cases.filter((c) => !/^synthetic$/i.test((c.provenance ?? '').trim())).length;
  if (cases.length > 0 && real / cases.length < MIN_REAL_PROVENANCE_SHARE) {
    fail(selectorCasesFile, `only ${real}/${cases.length} cases have real provenance; need ${Math.round(MIN_REAL_PROVENANCE_SHARE * 100)}%`);
  }
}

// ---------- 5. policy thresholds ----------
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
  const selector = policy.selector ?? {};
  if (!Number.isInteger(selector.maxMedianLenses) || selector.maxMedianLenses < 1) {
    fail(policyFile, 'selector.maxMedianLenses must be an integer >= 1');
  }
  if (!inUnit(selector.minLensPrecision) || selector.minLensPrecision === 0) {
    fail(policyFile, 'selector.minLensPrecision must be in (0, 1]');
  }
  if (!inUnit(selector.minMandatoryRecall) || selector.minMandatoryRecall === 0) {
    fail(policyFile, 'selector.minMandatoryRecall must be in (0, 1]');
  }
  if (!Number.isInteger(selector.maxProseCodeLensCases) || selector.maxProseCodeLensCases < 0) {
    fail(policyFile, 'selector.maxProseCodeLensCases must be an integer >= 0');
  }
  if (!inUnit(selector.maxTierEscalationRate)) {
    fail(policyFile, 'selector.maxTierEscalationRate must be in [0, 1]');
  }
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
  const selectorCasesPath = 'evals/selector/cases.json';
  if (changed.includes(selectorCasesPath)) {
    const before = gitShow(baseRef, selectorCasesPath);
    const currentPath = path.join(ROOT, selectorCasesPath);
    if (before !== null && existsSync(currentPath)) {
      const beforeVersion = JSON.parse(before).version;
      const afterVersion = readJson(currentPath)?.version;
      if (Number.isInteger(beforeVersion) && afterVersion <= beforeVersion) {
        fail(currentPath, `selector cases changed vs ${baseRef} but version was not bumped`);
      }
    }
  }
}

// ---------- report ----------
for (const w of warnings) console.log(`WARN  ${w}`);
for (const e of errors) console.log(`ERROR ${e}`);
console.log(`\n${taskFiles.length} golden tasks, ${taskTargets.size} resolved targets — ${errors.length} error(s), ${warnings.length} warning(s)`);
process.exit(errors.length > 0 ? 1 : 0);
