#!/usr/bin/env node

import { execFile as execFileCallback } from 'node:child_process';
import {
  mkdtempSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EXEC_TIMEOUT_MS = 25 * 60 * 1000;
const FINDING_LINE = /^\s*-\s+\[(P\d+)[·.-]([a-z]+(?:-[a-z]+)*)\]\s*(.*?)\s*$/i;
const LOCATION_SUFFIX = /^(.*?)(?:\s+[—–-]\s+`?([^`\r\n:]+):(\d+)`?)\s*$/;
const defaultExecFile = promisify(execFileCallback);

export function modelSlug(model) {
  const slug = String(model).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  return slug || 'model';
}

export function filterPairs(pairs, { includeLow = false, pairIds = null } = {}) {
  const requested = pairIds ? new Set(pairIds) : null;
  return pairs.filter((pair) => (
    (includeLow || pair.confidence !== 'low')
    && (!requested || requested.has(pair.id))
  ));
}

export function composeReviewPrompt({
  role,
  droidFile,
  culpritBaseSha,
  culpritHeadSha,
}) {
  return [
    `This is an evaluation of the \`${role}\` review contract. Read \`${droidFile}\` and perform a static review inline under that governing contract. Do not substitute another reviewer.`,
    `Review the change introduced by \`git diff ${culpritBaseSha}...${culpritHeadSha}\` in this repository.`,
    'Static review only: do not run tests or package commands, do not modify files.',
    'Emit findings using the contract\'s required `[P<n>·<confidence>] <title> — `path:line`` format.',
    '',
  ].join('\n');
}

export function parseFindingLines(result) {
  if (typeof result !== 'string') return [];
  return result.split(/\r?\n/).flatMap((raw) => {
    const match = raw.match(FINDING_LINE);
    if (!match) return [];
    const [, priority, confidence, rest] = match;
    const location = rest.match(LOCATION_SUFFIX);
    return [{
      title: (location ? location[1] : rest).trim(),
      path: location ? location[2] : null,
      line: location ? Number(location[3]) : null,
      priority,
      confidence,
      raw,
    }];
  });
}

export async function runReviewFixpairs({
  corpus,
  role,
  model,
  effort = null,
  reps = 1,
  pairs = null,
  includeLow = false,
  repo = '',
  execBin = 'droid',
  root = ROOT,
  runDroidExec = defaultExecFile,
  now = () => new Date(),
}) {
  if (!repo) throw new Error('--repo <path-to-clone> is required: the private clone path is supplied by the operator, never committed');
  const corpusData = readCorpus(corpus);
  const selectedPairs = filterPairs(corpusData.pairs, {
    includeLow,
    pairIds: pairs,
  });
  await requireCleanRepository(repo);
  const droidFile = findDroidFile(root, role);
  const contractSha = sha256(readFileSync(droidFile));
  const runStamp = utcStamp(now());
  const results = [];

  for (const pair of selectedPairs) {
    for (let rep = 1; rep <= reps; rep += 1) {
      results.push(await runOne({
        pair,
        role,
        model,
        effort,
        rep,
        repo,
        execBin,
        root,
        droidFile,
        contractSha,
        runStamp,
        runDroidExec,
        now,
      }));
    }
  }
  return results;
}

async function runOne({
  pair,
  role,
  model,
  effort,
  rep,
  repo,
  execBin,
  root,
  droidFile,
  contractSha,
  runStamp,
  runDroidExec,
  now,
}) {
  const runDir = path.join(
    root,
    'evals',
    'runs',
    `${runStamp}-fixpair-${pair.id}-${role}-${modelSlug(model)}-r${rep}`,
  );
  mkdirSync(runDir, { recursive: true });
  const prompt = composeReviewPrompt({ role, droidFile, ...pair });
  const promptFile = path.join(runDir, 'prompt.md');
  writeFileSync(promptFile, prompt);
  const worktree = mkdtempSync(path.join(tmpdir(), 'review-fixpair-'));
  const startedAt = now().toISOString();
  let envelope = null;
  let error = null;

  try {
    await runGit(repo, ['worktree', 'add', '--detach', worktree, pair.culpritHeadSha]);
    const args = ['exec', '-m', model];
    if (effort) args.push('-r', effort);
    args.push('-o', 'json', '-f', promptFile, '--cwd', worktree);
    const execution = await runDroidExec(execBin, args, {
      cwd: worktree,
      timeout: EXEC_TIMEOUT_MS,
      maxBuffer: 10 * 1024 * 1024,
    });
    envelope = parseEnvelope(execution.stdout);
    writeFileSync(path.join(runDir, 'result.json'), `${JSON.stringify(envelope, null, 2)}\n`);
    if (envelope.is_error) error = 'droid exec reported an error envelope';
  } catch (caught) {
    error = errorMessage(caught);
  } finally {
    try {
      await runGit(repo, ['worktree', 'remove', '--force', worktree]);
    } catch (cleanupError) {
      error ??= `worktree cleanup failed: ${errorMessage(cleanupError)}`;
    }
    rmSync(worktree, { recursive: true, force: true });
  }

  const finishedAt = now().toISOString();
  const findings = {
    schemaVersion: 1,
    pairId: pair.id,
    role,
    model,
    effort,
    rep,
    startedAt,
    finishedAt,
    durationMs: envelope?.duration_ms ?? null,
    usage: {
      factory_credits: envelope?.usage?.factory_credits ?? null,
      input_tokens: envelope?.usage?.input_tokens ?? null,
      output_tokens: envelope?.usage?.output_tokens ?? null,
    },
    contractSha,
    findings: error ? [] : parseFindingLines(envelope.result),
    error,
  };
  writeFileSync(path.join(runDir, 'findings.json'), `${JSON.stringify(findings, null, 2)}\n`);
  return { runDir, findings };
}

function readCorpus(corpus) {
  let parsed;
  try {
    parsed = JSON.parse(readFileSync(corpus, 'utf8'));
  } catch (error) {
    throw new Error(`cannot read corpus ${corpus}: ${errorMessage(error)}`);
  }
  if (parsed.schemaVersion !== 1 || !Array.isArray(parsed.pairs)) {
    throw new Error('corpus must have schemaVersion 1 and a pairs array');
  }
  return parsed;
}

function findDroidFile(root, role) {
  const matches = [];
  const plugins = path.join(root, 'plugins');
  for (const name of listDirectories(plugins)) {
    const candidate = path.join(plugins, name, 'droids', `${role}.md`);
    try {
      readFileSync(candidate);
      matches.push(candidate);
    } catch {
      // This plugin does not provide this role.
    }
  }
  if (matches.length !== 1) {
    throw new Error(`expected exactly one droid for role ${role}; found ${matches.length}`);
  }
  return matches[0];
}

function listDirectories(directory) {
  return readdirSync(directory, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name);
}

async function requireCleanRepository(repo) {
  const { stdout } = await runGit(repo, ['status', '--porcelain']);
  if (stdout.trim()) throw new Error(`repository is dirty: ${repo}`);
}

async function runGit(repo, args) {
  return defaultExecFile('git', ['-C', repo, ...args], { maxBuffer: 10 * 1024 * 1024 });
}

function parseEnvelope(stdout) {
  let envelope;
  try {
    envelope = JSON.parse(stdout);
  } catch {
    throw new Error('droid exec returned an unparseable JSON envelope');
  }
  if (
    !envelope
    || typeof envelope !== 'object'
    || envelope.type !== 'result'
    || typeof envelope.is_error !== 'boolean'
    || !Object.hasOwn(envelope, 'result')
  ) {
    throw new Error('droid exec returned an invalid JSON envelope');
  }
  return envelope;
}

function sha256(contents) {
  return createHash('sha256').update(contents).digest('hex');
}

function utcStamp(date) {
  return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
}

function errorMessage(error) {
  if (error?.killed || error?.code === 'ETIMEDOUT') return 'droid exec timed out';
  return error instanceof Error ? error.message : String(error);
}

function parseArgs(argv) {
  const options = { reps: 1, repo: '', execBin: 'droid', includeLow: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--include-low') {
      options.includeLow = true;
      continue;
    }
    const key = arg.replace(/^--/, '');
    if (!['corpus', 'role', 'model', 'effort', 'reps', 'pairs', 'repo', 'exec-bin'].includes(key)) {
      throw new Error(`unknown argument: ${arg}`);
    }
    options[key === 'exec-bin' ? 'execBin' : key] = argv[++index];
  }
  for (const key of ['corpus', 'role', 'model', 'repo']) {
    if (!options[key]) throw new Error(`missing --${key}`);
  }
  if (!['change-review', 'security'].includes(options.role)) {
    throw new Error('--role must be change-review or security');
  }
  options.reps = Number(options.reps);
  if (!Number.isInteger(options.reps) || options.reps < 1) throw new Error('--reps must be a positive integer');
  options.pairs = options.pairs ? options.pairs.split(',').filter(Boolean) : null;
  return options;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  await runReviewFixpairs(options);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch((error) => {
    process.stderr.write(`${errorMessage(error)}\n`);
    process.exitCode = 2;
  });
}
