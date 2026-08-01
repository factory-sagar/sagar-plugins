import { execFile as execFileCallback } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  assignConfidence,
  coalesceRanges,
  findDefectRegions,
  mineFixPairs,
  normalizeContent,
  parseBlamePorcelain,
  parseArgs,
  parseUnifiedDiff,
  sha1,
} from './mine-fix-pairs.mjs';

const execFile = promisify(execFileCallback);

test('parses unified diff deleted lines with pre-fix coordinates', () => {
  const files = parseUnifiedDiff([
    'diff --git a/src/example.js b/src/example.js',
    '--- a/src/example.js',
    '+++ b/src/example.js',
    '@@ -4,2 +4,2 @@',
    '-const enabled = true;',
    '+const enabled = false;',
    ' context',
  ].join('\n'));

  assert.deepEqual(files, [{
    oldPath: 'src/example.js',
    newPath: 'src/example.js',
    lines: [
      { type: 'delete', content: 'const enabled = true;', oldLine: 4, newLine: null },
      { type: 'add', content: 'const enabled = false;', oldLine: null, newLine: 4 },
      { type: 'context', content: 'context', oldLine: 5, newLine: 5 },
    ],
  }]);
});

test('parses porcelain blame records and normalizes content deterministically', () => {
  const blame = [
    'abcdef0123456789abcdef0123456789abcdef01 8 12 1',
    'author Example',
    'author-mail <example@example.test>',
    'filename src/example.js',
    '\tconst   enabled = true;',
    'abcdef0123456789abcdef0123456789abcdef01 9 13',
    '\t// comment only',
  ].join('\n');

  assert.deepEqual(parseBlamePorcelain(blame), [
    {
      sha: 'abcdef0123456789abcdef0123456789abcdef01',
      line: 12,
      content: 'const   enabled = true;',
    },
    {
      sha: 'abcdef0123456789abcdef0123456789abcdef01',
      line: 13,
      content: '// comment only',
    },
  ]);
  assert.equal(normalizeContent(' const   enabled = true;  '), 'const enabled = true;');
  assert.equal(sha1('const enabled = true;'), '1fe75e9657e780ba3165611382b9cb7e032a878f');
});

test('locates matching culprit additions and coalesces contiguous ranges', () => {
  const culpritDiff = [
    'diff --git a/src/example.js b/src/example.js',
    '--- a/src/example.js',
    '+++ b/src/example.js',
    '@@ -0,0 +1,4 @@',
    '+const enabled = true;',
    '+const name = "factory";',
    '+const retries = 3;',
    '+export { enabled, name, retries };',
  ].join('\n');
  const blamedLines = [
    { file: 'src/example.js', content: 'const enabled = true;' },
    { file: 'src/example.js', content: 'const name = "factory";' },
    { file: 'src/example.js', content: 'missing line' },
  ];

  const result = findDefectRegions(blamedLines, parseUnifiedDiff(culpritDiff));

  assert.deepEqual(result.defectLines, [{
    file: 'src/example.js',
    contentHashes: [
      sha1('const enabled = true;'),
      sha1('const name = "factory";'),
    ],
    culpritAddedLines: [[1, 2]],
  }]);
  assert.equal(result.resolvedCount, 2);
  assert.deepEqual(coalesceRanges([7, 2, 3, 4, 9]), [[2, 4], [7, 7], [9, 9]]);
});

test('prefers the closest matching culprit addition in the same file', () => {
  const culpritDiff = [
    'diff --git a/src/example.js b/src/example.js',
    '--- a/src/example.js',
    '+++ b/src/example.js',
    '@@ -0,0 +1,1 @@',
    '+const enabled = true;',
    '@@ -9,0 +10,1 @@',
    '+const enabled = true;',
  ].join('\n');

  const result = findDefectRegions(
    [{ file: 'src/example.js', line: 10, content: 'const enabled = true;' }],
    parseUnifiedDiff(culpritDiff),
  );

  assert.deepEqual(result.defectLines[0].culpritAddedLines, [[10, 10]]);
});

test('falls back to a matching addition in a renamed file', () => {
  const culpritDiff = [
    'diff --git a/src/old.js b/src/new.js',
    '--- /dev/null',
    '+++ b/src/new.js',
    '@@ -0,0 +1,1 @@',
    '+const enabled = true;',
  ].join('\n');

  const result = findDefectRegions(
    [{ file: 'src/old.js', line: 1, content: 'const enabled = true;' }],
    parseUnifiedDiff(culpritDiff),
  );

  assert.deepEqual(result.defectLines, [{
    file: 'src/new.js',
    contentHashes: [sha1('const enabled = true;')],
    culpritAddedLines: [[1, 1]],
  }]);
});

test('assigns confidence from attribution and resolution', () => {
  assert.equal(assignConfidence({ isRevert: true, culpritPrCount: 1, resolvedCount: 0, totalCount: 1 }), 'high');
  assert.equal(assignConfidence({ isRevert: false, culpritPrCount: 1, resolvedCount: 2, totalCount: 2 }), 'high');
  assert.equal(assignConfidence({ isRevert: false, culpritPrCount: 1, resolvedCount: 1, totalCount: 2 }), 'medium');
  assert.equal(assignConfidence({ isRevert: false, culpritPrCount: 4, resolvedCount: 4, totalCount: 4 }), 'low');
});

test('rejects invalid numeric CLI options', () => {
  assert.throws(
    () => parseArgs(['--max-fix-lines', 'not-a-number']),
    /finite non-negative integer/,
  );
});

test('mines a synthetic fix pair through git with injected PR metadata', async (t) => {
  const repo = await mkdtemp(join(tmpdir(), 'mine-fix-pairs-'));
  t.after(() => rm(repo, { recursive: true, force: true }));

  const git = async (...args) => {
    const { stdout } = await execFile('git', args, { cwd: repo });
    return stdout.trim();
  };
  await git('init', '--initial-branch=main');
  await git('config', 'user.email', 'test@example.test');
  await git('config', 'user.name', 'Test User');
  await writeFile(join(repo, 'feature.js'), 'const enabled = false;\n');
  await git('add', 'feature.js');
  await git('commit', '-m', 'chore: initial');
  const initialSha = await git('rev-parse', 'HEAD');

  await writeFile(join(repo, 'feature.js'), 'const enabled = true;\n');
  await git('commit', '-am', 'feat: introduce regression');
  const culpritSha = await git('rev-parse', 'HEAD');

  await writeFile(join(repo, 'feature.js'), 'const enabled = false;\n');
  await git('commit', '-am', 'fix: correct enabled default');
  const fixSha = await git('rev-parse', 'HEAD');

  const metadata = (culpritMergeCommitSha = culpritSha) => ({
    async listFixPrs() {
      return [{ number: 200, title: 'fix: correct enabled default', mergeCommit: fixSha, mergedAt: new Date().toISOString() }];
    },
    async getPullRequest(number) {
      if (number === 200) {
        return { additions: 1, deletions: 1 };
      }
      assert.equal(number, 100);
      return {
        number: 100,
        title: 'feat: introduce regression',
        state: 'MERGED',
        mergedAt: new Date().toISOString(),
        baseRefOid: initialSha,
        headRefOid: '0000000000000000000000000000000000000000',
        mergeCommitSha: culpritMergeCommitSha,
        additions: 1,
        deletions: 1,
      };
    },
    async getCommitPulls(sha) {
      return sha === culpritSha ? [{ number: 100, state: 'MERGED' }] : [];
    },
  });

  const corpus = await mineFixPairs({
    repo,
    base: 'main',
    days: 120,
    limit: 25,
    maxFixLines: 10,
    minCulpritLines: 1,
    maxCulpritLines: 10,
    metadata: metadata(),
  });

  assert.equal(corpus.pairs.length, 1);
  assert.deepEqual(corpus.pairs[0], {
    id: 'fp-0001',
    fixPr: 200,
    culpritPr: 100,
    culpritBaseSha: initialSha,
    culpritHeadSha: culpritSha,
    confidence: 'high',
    changedFiles: ['feature.js'],
    defectLines: [{
      file: 'feature.js',
      contentHashes: [sha1('const enabled = true;')],
      culpritAddedLines: [[1, 1]],
    }],
    culpritChangedLines: 2,
    sizeClass: 'medium',
  });

  for (const mergeCommitSha of [null, '0000000000000000000000000000000000000000']) {
    const skipped = await mineFixPairs({
      repo,
      base: 'main',
      days: 120,
      limit: 25,
      maxFixLines: 10,
      minCulpritLines: 1,
      maxCulpritLines: 10,
      metadata: metadata(mergeCommitSha),
    });
    assert.equal(skipped.pairs.length, 0);
  }
});
