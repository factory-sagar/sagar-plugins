#!/usr/bin/env node
// Structural invariant validator for the sagar-plugins marketplace.
//
//   node scripts/validate.mjs                       # full structural validation
//   node scripts/validate.mjs --require-bumps REF   # + require plugin.json (and changed SKILL.md)
//                                                   #   version bumps vs git REF (e.g. origin/main)
//
// Dependency-free by design: parses only the YAML subset these files use
// (scalar values, block scalars via |, flow arrays, booleans).

import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync, existsSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const errors = [];
const warnings = [];
const fail = (file, msg) => errors.push(`${path.relative(ROOT, file)}: ${msg}`);
const warn = (file, msg) => warnings.push(`${path.relative(ROOT, file)}: ${msg}`);

// Model allowlist and per-model reasoningEffort compatibility.
// Source of truth is the CLI's embedded model registry, NOT the docs page (which lags —
// it omitted glm-5.2's `max`, for example). Re-extract when models change:
//   rg -a -o '"<model>":\{id:"<model>".{0,700}?reasoningEffort:\{supported:\[[^\]]*\]' "$(which droid)"
// A typo'd slug or an unsupported effort silently degrades a droid.
const EFFORT_BY_MODEL = {
  'claude-fable-5': ['off', 'low', 'medium', 'high', 'xhigh', 'max'],
  'glm-5.2': ['off', 'high', 'max'],
  'glm-5.1': ['off', 'high'],
  'kimi-k2.6': ['off', 'high'],
  'gpt-5.5': ['low', 'medium', 'high', 'xhigh'],
  'gpt-5.4': ['low', 'medium', 'high', 'xhigh'],
  'gpt-5.2': ['off', 'low', 'medium', 'high', 'xhigh'],
  'claude-opus-4-8': ['off', 'low', 'medium', 'high', 'xhigh', 'max'],
  'claude-opus-4-7': ['off', 'low', 'medium', 'high', 'xhigh', 'max'],
  'claude-sonnet-4-6': ['off', 'low', 'medium', 'high', 'max'],
};
// Repo policy (README "Models"): no `inherit` — pinned slugs keep droid output
// distribution independent of the parent session, and effort is ignored under inherit.
const FORBID_INHERIT = true;

const VALID_TOOLS = new Set([
  'Read', 'LS', 'Grep', 'Glob', 'Create', 'Edit', 'ApplyPatch',
  'Execute', 'WebSearch', 'FetchUrl',
]);
const VALID_TOOL_CATEGORIES = new Set(['read-only', 'edit', 'execute', 'web', 'mcp']);
const SEMVER = /^\d+\.\d+\.\d+$/;

// ---------- tiny YAML-subset parser ----------
function parseFrontmatter(file, text) {
  if (!text.startsWith('---\n')) return null;
  const end = text.indexOf('\n---\n', 4);
  if (end === -1) return null;
  const raw = text.slice(4, end);
  const body = text.slice(end + 5);
  const data = {};
  const lines = raw.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim() || /^\s*#/.test(line)) continue;
    const m = line.match(/^([A-Za-z][\w-]*):\s*(.*)$/);
    if (!m) { fail(file, `frontmatter line not parseable: "${line}"`); continue; }
    const [, key, rest] = m;
    if (rest === '|' || rest === '|-') {
      const block = [];
      while (i + 1 < lines.length && (/^\s{2,}/.test(lines[i + 1]) || lines[i + 1].trim() === '')) {
        block.push(lines[++i].replace(/^\s{2}/, ''));
      }
      data[key] = block.join('\n').trim();
    } else if (rest.startsWith('[')) {
      data[key] = rest.replace(/^\[|\]$/g, '').split(',')
        .map((s) => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
    } else {
      data[key] = rest.replace(/^["']|["']$/g, '').trim();
    }
  }
  return { data, body };
}

const read = (f) => readFileSync(f, 'utf8');
const readJson = (f) => {
  try { return JSON.parse(read(f)); }
  catch (e) { fail(f, `invalid JSON: ${e.message}`); return null; }
};
const listDirs = (p) => existsSync(p)
  ? readdirSync(p).filter((d) => !d.startsWith('.') && statSync(path.join(p, d)).isDirectory())
  : [];
const listMd = (p) => existsSync(p)
  ? readdirSync(p).filter((f) => f.endsWith('.md')).map((f) => path.join(p, f))
  : [];

// ---------- collect fleet ----------
const pluginsDir = path.join(ROOT, 'plugins');
const pluginDirs = listDirs(pluginsDir);
const droidFiles = pluginDirs.flatMap((p) => listMd(path.join(pluginsDir, p, 'droids')));
const commandFiles = pluginDirs.flatMap((p) => listMd(path.join(pluginsDir, p, 'commands')));
const skillFiles = pluginDirs.flatMap((p) => {
  const skillsRoot = path.join(pluginsDir, p, 'skills');
  return listDirs(skillsRoot).map((s) => path.join(skillsRoot, s, 'SKILL.md'));
});
const fleetNames = new Set();

// ---------- 1. marketplace.json <-> plugin dirs/manifests ----------
const marketplaceFile = path.join(ROOT, '.factory-plugin', 'marketplace.json');
const marketplace = readJson(marketplaceFile);
if (marketplace) {
  if (!marketplace.name || !marketplace.owner?.name) fail(marketplaceFile, 'missing name or owner.name');
  const entries = new Map((marketplace.plugins ?? []).map((p) => [p.name, p]));
  if (entries.size !== (marketplace.plugins ?? []).length) fail(marketplaceFile, 'duplicate plugin names');
  for (const [name, entry] of entries) {
    if (!entry.description) fail(marketplaceFile, `plugin "${name}" missing description`);
    if (!entry.category) warn(marketplaceFile, `plugin "${name}" missing category`);
    const src = path.join(ROOT, entry.source ?? '');
    if (!entry.source || !existsSync(src)) fail(marketplaceFile, `plugin "${name}" source does not exist: ${entry.source}`);
  }
  for (const dir of pluginDirs) {
    if (!entries.has(dir)) fail(marketplaceFile, `plugins/${dir} exists on disk but has no marketplace entry`);
  }
  for (const name of entries.keys()) {
    if (!pluginDirs.includes(name)) fail(marketplaceFile, `marketplace entry "${name}" has no plugins/${name} directory`);
  }
  for (const dir of pluginDirs) {
    const manifestFile = path.join(pluginsDir, dir, '.factory-plugin', 'plugin.json');
    if (!existsSync(manifestFile)) { fail(manifestFile, 'missing plugin.json'); continue; }
    const manifest = readJson(manifestFile);
    if (!manifest) continue;
    if (manifest.name !== dir) fail(manifestFile, `name "${manifest.name}" != directory "${dir}"`);
    if (!SEMVER.test(manifest.version ?? '')) fail(manifestFile, `version "${manifest.version}" is not X.Y.Z semver`);
    if (!manifest.description) fail(manifestFile, 'missing description');
    if (!manifest.author?.name) fail(manifestFile, 'missing author.name');
    const entry = entries.get(dir);
    if (entry && manifest.description !== entry.description) {
      fail(manifestFile, `description differs from marketplace.json entry — they must be byte-identical (drift guard)`);
    }
  }
}

// ---------- 2. droid frontmatter ----------
for (const file of droidFiles) {
  const fm = parseFrontmatter(file, read(file));
  if (!fm) { fail(file, 'missing or unterminated YAML frontmatter'); continue; }
  const { data, body } = fm;
  const base = path.basename(file, '.md');
  fleetNames.add(data.name);
  if (data.name !== base) fail(file, `name "${data.name}" != filename "${base}"`);
  if (!data.description) fail(file, 'missing description');
  else if (data.description.length > 500) fail(file, `description is ${data.description.length} chars (max 500)`);
  if (!data.model) fail(file, 'missing model');
  else if (data.model === 'inherit') {
    if (FORBID_INHERIT) fail(file, 'model "inherit" violates repo policy: pin a slug (README "Models")');
  } else if (!EFFORT_BY_MODEL[data.model]) {
    fail(file, `model "${data.model}" not in allowlist — check docs.factory.ai/models, then extend EFFORT_BY_MODEL`);
  } else {
    if (!data.reasoningEffort) fail(file, `missing reasoningEffort — pin it explicitly (repo policy)`);
    else if (!EFFORT_BY_MODEL[data.model].includes(data.reasoningEffort)) {
      fail(file, `reasoningEffort "${data.reasoningEffort}" unsupported by ${data.model} (valid: ${EFFORT_BY_MODEL[data.model].join(', ')})`);
    }
  }
  if (!data.tools) warn(file, 'no tools declared — droid gets all tools');
  else if (Array.isArray(data.tools)) {
    for (const t of data.tools) if (!VALID_TOOLS.has(t)) fail(file, `unknown tool ID "${t}"`);
  } else if (!VALID_TOOL_CATEGORIES.has(data.tools)) {
    fail(file, `unknown tools category "${data.tools}"`);
  }
  if (!body.trim()) fail(file, 'empty prompt body');
  if (!/^## Output/m.test(body)) fail(file, 'no "## Output" contract section — every droid declares its output shape');
}

// ---------- 3. skill + command frontmatter ----------
for (const file of skillFiles) {
  if (!existsSync(file)) { fail(file, 'skill directory missing SKILL.md'); continue; }
  const fm = parseFrontmatter(file, read(file));
  if (!fm) { fail(file, 'missing or unterminated YAML frontmatter'); continue; }
  const dirName = path.basename(path.dirname(file));
  fleetNames.add(fm.data.name);
  if (fm.data.name !== dirName) fail(file, `name "${fm.data.name}" != directory "${dirName}"`);
  if (!SEMVER.test(fm.data.version ?? '')) fail(file, `version "${fm.data.version}" is not X.Y.Z semver`);
  if (!fm.data.description) fail(file, 'missing description');
  if (!fm.body.trim()) fail(file, 'empty skill body');
}
for (const file of commandFiles) {
  const fm = parseFrontmatter(file, read(file));
  if (!fm) { fail(file, 'missing or unterminated YAML frontmatter'); continue; }
  if (!fm.data.description) fail(file, 'missing description');
}

// ---------- 4. README counts ----------
const readmeFile = path.join(ROOT, 'README.md');
const readme = read(readmeFile);
const totals = readme.match(/Total: (\d+) droids, (\d+) skills, (\d+) commands?/);
if (!totals) fail(readmeFile, 'no "Total: X droids, Y skills, Z commands" line found');
else {
  const [, d, s, c] = totals.map(Number);
  if (d !== droidFiles.length) fail(readmeFile, `README says ${d} droids, filesystem has ${droidFiles.length}`);
  if (s !== skillFiles.length) fail(readmeFile, `README says ${s} skills, filesystem has ${skillFiles.length}`);
  if (c !== commandFiles.length) fail(readmeFile, `README says ${c} commands, filesystem has ${commandFiles.length}`);
}

// ---------- 5. relative .md cross-references resolve ----------
function* walkMd(dir) {
  for (const entry of readdirSync(dir)) {
    if (entry.startsWith('.')) continue;
    const p = path.join(dir, entry);
    if (statSync(p).isDirectory()) yield* walkMd(p);
    else if (entry.endsWith('.md')) yield p;
  }
}
const REL_REF = /(?:^|[\s`("'])((?:\.\.\/)+[\w./-]+\.md)/g;
for (const file of [...walkMd(pluginsDir)]) {
  const text = read(file);
  for (const [, ref] of text.matchAll(REL_REF)) {
    if (ref.includes('*')) continue;
    if (!existsSync(path.resolve(path.dirname(file), ref))) {
      fail(file, `relative reference does not resolve: ${ref}`);
    }
  }
}

// ---------- 6. golden tasks ----------
const goldensDir = path.join(ROOT, 'evals', 'golden-tasks');
const taskFiles = existsSync(goldensDir)
  ? readdirSync(goldensDir).filter((f) => /^\d{2}-.*\.md$/.test(f))
  : [];
const goldensReadme = path.join(goldensDir, 'README.md');
if (existsSync(goldensReadme)) {
  const grText = read(goldensReadme);
  for (const f of taskFiles) {
    if (!grText.includes(f)) fail(goldensReadme, `task file ${f} not listed in the Tasks table`);
  }
}
for (const f of taskFiles) {
  const file = path.join(goldensDir, f);
  const m = read(file).match(/## Target\n+([^\n]+)/);
  if (!m) { fail(file, 'no "## Target" section'); continue; }
  const named = [...m[1].matchAll(/`([\w-]+)`/g)].map(([, n]) => n);
  if (named.length === 0) fail(file, `Target line names no backticked droid/skill: "${m[1]}"`);
  for (const n of named) {
    if (!fleetNames.has(n)) fail(file, `Target "${n}" is not a droid or skill in this marketplace`);
  }
}

// ---------- 7. version bumps vs a base ref ----------
const bumpIdx = process.argv.indexOf('--require-bumps');
if (bumpIdx !== -1) {
  const baseRef = process.argv[bumpIdx + 1];
  if (!baseRef) { console.error('--require-bumps requires a git ref'); process.exit(2); }
  const git = (...args) =>
    execFileSync('git', args, { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
  const gitShow = (ref, p) => {
    try { return git('show', `${ref}:${p}`); } catch { return null; }
  };
  const changed = git('diff', '--name-only', `${baseRef}...HEAD`).split('\n').filter(Boolean);
  const touchedPlugins = new Set(
    changed.map((f) => f.match(/^plugins\/([^/]+)\//)?.[1]).filter(Boolean),
  );
  for (const p of touchedPlugins) {
    const manifestPath = `plugins/${p}/.factory-plugin/plugin.json`;
    const before = gitShow(baseRef, manifestPath);
    const after = read(path.join(ROOT, manifestPath));
    if (before !== null && JSON.parse(before).version === JSON.parse(after).version) {
      fail(path.join(ROOT, manifestPath), `plugins/${p} changed vs ${baseRef} but version was not bumped`);
    }
  }
  for (const f of changed.filter((f) => f.endsWith('/SKILL.md') && f.startsWith('plugins/'))) {
    const before = gitShow(baseRef, f);
    if (before === null) continue; // new skill
    const vBefore = before.match(/^version: (.+)$/m)?.[1];
    const vAfter = read(path.join(ROOT, f)).match(/^version: (.+)$/m)?.[1];
    if (vBefore && vBefore === vAfter) fail(path.join(ROOT, f), `SKILL.md changed vs ${baseRef} but frontmatter version was not bumped`);
  }
}

// ---------- report ----------
for (const w of warnings) console.log(`WARN  ${w}`);
for (const e of errors) console.log(`ERROR ${e}`);
console.log(`\n${droidFiles.length} droids, ${skillFiles.length} skills, ${commandFiles.length} commands, ${taskFiles.length} golden tasks — ${errors.length} error(s), ${warnings.length} warning(s)`);
process.exit(errors.length > 0 ? 1 : 0);
