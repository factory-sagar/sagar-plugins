import assert from 'node:assert/strict';
import { execFile as execFileCallback, spawnSync } from 'node:child_process';
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { promisify } from 'node:util';

import {
  composeReviewPrompt,
  filterPairs,
  modelSlug,
  parseFindingLines,
  runReviewFixpairs,
} from './run-review-fixpairs.mjs';

const execFile = promisify(execFileCallback);

test('parses finding lines with dash and backtick variants', () => {
  const findings = parseFindingLines([
    '- [P1·high] Prevent replay — `src/auth.ts:42`',
    '- [P2-low-med] Preserve the parser – lib/read.js:7',
    '- [P3.low] No location supplied',
    'not a finding',
  ].join('\n'));

  assert.deepEqual(findings, [
    {
      title: 'Prevent replay',
      path: 'src/auth.ts',
      line: 42,
      priority: 'P1',
      confidence: 'high',
      raw: '- [P1·high] Prevent replay — `src/auth.ts:42`',
    },
    {
      title: 'Preserve the parser',
      path: 'lib/read.js',
      line: 7,
      priority: 'P2',
      confidence: 'low-med',
      raw: '- [P2-low-med] Preserve the parser – lib/read.js:7',
    },
    {
      title: 'No location supplied',
      path: null,
      line: null,
      priority: 'P3',
      confidence: 'low',
      raw: '- [P3.low] No location supplied',
    },
  ]);
});

test('composes the governing-contract review preamble', () => {
  const prompt = composeReviewPrompt({
    role: 'change-review',
    droidFile: '/tmp/repo/plugins/review/droids/change-review.md',
    culpritBaseSha: 'base-sha',
    culpritHeadSha: 'head-sha',
  });

  assert.match(prompt, /change-review/);
  assert.match(prompt, /\/tmp\/repo\/plugins\/review\/droids\/change-review\.md/);
  assert.match(prompt, /base-sha\.\.\.head-sha/);
  assert.match(prompt, /Static review only/);
});

test('filters low-confidence pairs unless requested and slugs models', () => {
  const pairs = [
    { id: 'fp-0001', confidence: 'high' },
    { id: 'fp-0002', confidence: 'low' },
  ];
  assert.deepEqual(filterPairs(pairs, { includeLow: false }).map(({ id }) => id), ['fp-0001']);
  assert.deepEqual(filterPairs(pairs, { includeLow: true }).map(({ id }) => id), ['fp-0001', 'fp-0002']);
  assert.equal(modelSlug('factory/model:large v2'), 'factory-model-large-v2');
});

test('creates artifacts, uses a detached worktree, and removes it after success', async (t) => {
  const fixture = makeFixture();
  t.after(() => rmSync(fixture.root, { recursive: true, force: true }));
  const calls = [];

  const results = await runReviewFixpairs({
    corpus: fixture.corpus,
    role: 'change-review',
    model: 'test/model',
    reps: 1,
    repo: fixture.repo,
    root: fixture.root,
    runDroidExec: async (command, args, options) => {
      calls.push({ command, args, options });
      return {
        stdout: JSON.stringify(successEnvelope('- [P1·high] Fix boundary — `src/value.js:2`')),
        stderr: '',
      };
    },
  });

  assert.equal(results.length, 1);
  const runDir = results[0].runDir;
  const findingFile = JSON.parse(readFileSync(path.join(runDir, 'findings.json'), 'utf8'));
  assert.equal(findingFile.findings[0].path, 'src/value.js');
  assert.equal(findingFile.findings[0].line, 2);
  assert.equal(findingFile.error, null);
  assert.match(readFileSync(path.join(runDir, 'prompt.md'), 'utf8'), new RegExp(fixture.baseSha));
  assert.match(readFileSync(path.join(runDir, 'prompt.md'), 'utf8'), new RegExp(fixture.headSha));
  assert.match(readFileSync(path.join(runDir, 'prompt.md'), 'utf8'), /plugins\/review\/droids\/change-review\.md/);
  assert.deepEqual(calls[0].args.slice(0, 6), ['exec', '-m', 'test/model', '-o', 'json', '-f']);
  assert.equal(calls[0].options.cwd.includes('review-fixpair-'), true);
  const worktrees = await execFile('git', ['-C', fixture.repo, 'worktree', 'list', '--porcelain']);
  assert.doesNotMatch(worktrees.stdout, /review-fixpair-/);
});

test('writes an error artifact and cleans up its worktree after exec failure', async (t) => {
  const fixture = makeFixture();
  t.after(() => rmSync(fixture.root, { recursive: true, force: true }));

  const [result] = await runReviewFixpairs({
    corpus: fixture.corpus,
    role: 'change-review',
    model: 'test/model',
    repo: fixture.repo,
    root: fixture.root,
    runDroidExec: async () => {
      throw new Error('stub exited 1');
    },
  });

  const findings = JSON.parse(readFileSync(path.join(result.runDir, 'findings.json'), 'utf8'));
  assert.deepEqual(findings.findings, []);
  assert.match(findings.error, /stub exited 1/);
  const worktrees = await execFile('git', ['-C', fixture.repo, 'worktree', 'list', '--porcelain']);
  assert.doesNotMatch(worktrees.stdout, /review-fixpair-/);
});

function makeFixture() {
  const root = mkdtempSync(path.join(tmpdir(), 'review-fixpairs-test-'));
  const repo = path.join(root, 'subject');
  mkdirSync(repo);
  writeFileSync(path.join(root, 'package.json'), '{"type":"module"}\n');
  mkdirSync(path.join(root, 'plugins', 'review', 'droids'), { recursive: true });
  writeFileSync(
    path.join(root, 'plugins', 'review', 'droids', 'change-review.md'),
    '---\nname: change-review\n---\nReview changes.\n',
  );
  runGit(repo, ['init']);
  runGit(repo, ['config', 'user.email', 'test@example.com']);
  runGit(repo, ['config', 'user.name', 'Test']);
  mkdirSync(path.join(repo, 'src'));
  writeFileSync(path.join(repo, 'src', 'value.js'), 'export const value = 1;\n');
  runGit(repo, ['add', '.']);
  runGit(repo, ['commit', '-m', 'base']);
  const baseSha = runGit(repo, ['rev-parse', 'HEAD']).trim();
  writeFileSync(path.join(repo, 'src', 'value.js'), 'export const value = 2;\n');
  runGit(repo, ['commit', '-am', 'culprit']);
  const headSha = runGit(repo, ['rev-parse', 'HEAD']).trim();
  const corpus = path.join(root, 'corpus.json');
  writeFileSync(corpus, JSON.stringify({
    schemaVersion: 1,
    pairs: [{
      id: 'fp-0001',
      culpritBaseSha: baseSha,
      culpritHeadSha: headSha,
      confidence: 'high',
    }],
  }));
  return { root, repo, corpus, baseSha, headSha };
}

function runGit(cwd, args) {
  return requireSync('git', ['-C', cwd, ...args]);
}

function requireSync(command, args) {
  const result = spawnSync(command, args, { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr);
  return result.stdout;
}

function successEnvelope(result) {
  return {
    type: 'result',
    subtype: 'success',
    is_error: false,
    duration_ms: 123,
    num_turns: 1,
    result,
    session_id: 'session',
    usage: {
      input_tokens: 10,
      output_tokens: 20,
      cache_read_input_tokens: 0,
      cache_creation_input_tokens: 0,
      factory_credits: 0.25,
      thinking_tokens: 5,
    },
  };
}
