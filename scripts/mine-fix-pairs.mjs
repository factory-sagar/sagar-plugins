#!/usr/bin/env node
import { execFile as execFileCallback } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve, sep } from 'node:path';
import { promisify } from 'node:util';

const execFile = promisify(execFileCallback);

/**
 * Normalizes source content before matching it across independently produced diffs.
 *
 * @param {string} content source line
 * @returns {string} trimmed, whitespace-collapsed content
 */
export function normalizeContent(content) {
  return content.trim().replace(/\s+/g, ' ');
}

/**
 * Hashes normalized source content.
 *
 * @param {string} content normalized source line
 * @returns {string} lowercase SHA-1 digest
 */
export function sha1(content) {
  return createHash('sha1').update(content).digest('hex');
}

/**
 * Identifies content that cannot usefully identify a defect origin.
 *
 * @param {string} content source line
 * @returns {boolean} whether the line is blank or entirely a comment
 */
export function isIgnorableBlameContent(content) {
  const trimmed = content.trim();
  return trimmed === '' || /^(?:\/\/|\/\*|\*\/|\*|#)/.test(trimmed);
}

/**
 * Parses a unified diff into files and line coordinates.
 *
 * @param {string} diff unified diff text
 * @returns {Array<{oldPath: string, newPath: string, lines: Array<{type: string, content: string, oldLine: number | null, newLine: number | null}>}>}
 */
export function parseUnifiedDiff(diff) {
  const files = [];
  let file = null;
  let oldLine = 0;
  let newLine = 0;

  for (const line of diff.split('\n')) {
    if (line.startsWith('diff --git ')) {
      const match = /^diff --git a\/(.+) b\/(.+)$/.exec(line);
      file = match === null ? null : { oldPath: match[1], newPath: match[2], lines: [] };
      if (file !== null) files.push(file);
      continue;
    }
    if (file === null) continue;
    if (line.startsWith('--- ') || line.startsWith('+++ ')) continue;
    const hunk = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/.exec(line);
    if (hunk !== null) {
      oldLine = Number(hunk[1]);
      newLine = Number(hunk[3]);
      continue;
    }
    if (line.startsWith('\\ No newline')) continue;
    if (line.startsWith('-')) {
      file.lines.push({ type: 'delete', content: line.slice(1), oldLine, newLine: null });
      oldLine += 1;
    } else if (line.startsWith('+')) {
      file.lines.push({ type: 'add', content: line.slice(1), oldLine: null, newLine });
      newLine += 1;
    } else if (line.startsWith(' ')) {
      file.lines.push({ type: 'context', content: line.slice(1), oldLine, newLine });
      oldLine += 1;
      newLine += 1;
    }
  }
  return files;
}

/**
 * Parses the source line records from git blame --porcelain output.
 *
 * @param {string} output porcelain blame output
 * @returns {Array<{sha: string, line: number, content: string}>}
 */
export function parseBlamePorcelain(output) {
  const lines = output.split('\n');
  const results = [];
  let pending = null;
  for (const line of lines) {
    const header = /^([0-9a-f]{40}) \d+ (\d+)(?: \d+)?$/.exec(line);
    if (header !== null) {
      pending = { sha: header[1], line: Number(header[2]) };
    } else if (pending !== null && line.startsWith('\t')) {
      results.push({ ...pending, content: line.slice(1) });
      pending = null;
    }
  }
  return results;
}

/**
 * Coalesces line numbers into sorted inclusive ranges.
 *
 * @param {Array<number>} numbers line numbers
 * @returns {Array<[number, number]>} contiguous ranges
 */
export function coalesceRanges(numbers) {
  const sorted = [...new Set(numbers)].sort((left, right) => left - right);
  const ranges = [];
  for (const number of sorted) {
    const prior = ranges.at(-1);
    if (prior !== undefined && number === prior[1] + 1) {
      prior[1] = number;
    } else {
      ranges.push([number, number]);
    }
  }
  return ranges;
}

/**
 * Matches blamed pre-fix lines against additions in a culprit PR diff.
 *
 * @param {Array<{file: string, content: string}>} blamedLines source lines attributed to one culprit PR
 * @param {ReturnType<typeof parseUnifiedDiff>} culpritFiles culprit PR diff
 * @returns {{defectLines: Array<{file: string, contentHashes: Array<string>, culpritAddedLines: Array<[number, number]>}>, resolvedCount: number}} Ranges are in the culprit merge-commit tree.
 */
export function findDefectRegions(blamedLines, culpritFiles) {
  const additions = new Map();
  for (const file of culpritFiles) {
    for (const line of file.lines) {
      if (line.type !== 'add' || isIgnorableBlameContent(line.content)) continue;
      const key = sha1(normalizeContent(line.content));
      const matches = additions.get(key) ?? [];
      matches.push({ file: file.newPath, line: line.newLine });
      additions.set(key, matches);
    }
  }

  const matched = new Map();
  let resolvedCount = 0;
  for (const blamed of blamedLines) {
    const normalized = normalizeContent(blamed.content);
    if (isIgnorableBlameContent(normalized)) continue;
    const contentHash = sha1(normalized);
    const candidates = additions.get(contentHash);
    if (candidates === undefined) continue;
    const closest = candidates.reduce((best, candidate) => {
      const bestRank = [best.file === blamed.file ? 0 : 1, Math.abs(best.line - (blamed.line ?? best.line))];
      const candidateRank = [candidate.file === blamed.file ? 0 : 1, Math.abs(candidate.line - (blamed.line ?? candidate.line))];
      return candidateRank[0] < bestRank[0] || (candidateRank[0] === bestRank[0] && candidateRank[1] < bestRank[1])
        ? candidate
        : best;
    });
    const entry = matched.get(closest.file) ?? { hashes: [], lines: [] };
    entry.hashes.push(contentHash);
    entry.lines.push(closest.line);
    matched.set(closest.file, entry);
    resolvedCount += 1;
  }

  return {
    defectLines: [...matched.entries()].map(([file, entry]) => ({
      file,
      contentHashes: [...new Set(entry.hashes)],
      culpritAddedLines: coalesceRanges(entry.lines),
    })),
    resolvedCount,
  };
}

/**
 * Assigns the corpus confidence label from settled attribution rules.
 *
 * @param {{isRevert: boolean, culpritPrCount: number, resolvedCount: number, totalCount: number}} input evidence counts
 * @returns {'high' | 'medium' | 'low'} confidence label
 */
export function assignConfidence({ isRevert, culpritPrCount, resolvedCount, totalCount }) {
  if (isRevert) return 'high';
  if (culpritPrCount > 3) return 'low';
  if (culpritPrCount === 1 && resolvedCount === totalCount) return 'high';
  return 'medium';
}

async function run(repo, command, args) {
  const { stdout } = await execFile(command, args, { cwd: repo, maxBuffer: 16 * 1024 * 1024 });
  return stdout;
}

async function git(repo, ...args) {
  return run(repo, 'git', args);
}

async function hasCommit(repo, sha) {
  return git(repo, 'cat-file', '-e', `${sha}^{commit}`)
    .then(() => true)
    .catch(() => false);
}

function changedLines(pr) {
  return Number(pr.additions ?? 0) + Number(pr.deletions ?? 0);
}

function metadataSource(ghRepo) {
  if (!ghRepo) {
    throw new Error('--gh-repo <owner/name> is required: the private repository slug is supplied by the operator, never committed');
  }
  return {
    async listFixPrs({ days, limit }) {
      const { stdout } = await execFile('gh', [
        'pr', 'list', '--repo', ghRepo, '--state', 'merged',
        '--search', 'fix in:title', '--json', 'number,title,mergeCommit,mergedAt', '--limit', String(limit),
      ], { maxBuffer: 16 * 1024 * 1024 });
      const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
      return JSON.parse(stdout).filter((pr) => Date.parse(pr.mergedAt) >= cutoff);
    },
    async getPullRequest(number) {
      const { stdout } = await execFile('gh', [
        'api', `repos/${ghRepo}/pulls/${number}`,
      ], { maxBuffer: 16 * 1024 * 1024 });
      const pr = JSON.parse(stdout);
      return {
        number: pr.number,
        title: pr.title,
        state: pr.merged_at === null ? pr.state.toUpperCase() : 'MERGED',
        mergedAt: pr.merged_at,
        baseRefOid: pr.base?.sha,
        headRefOid: pr.head?.sha,
        mergeCommitSha: pr.merge_commit_sha,
        additions: pr.additions,
        deletions: pr.deletions,
      };
    },
    async getCommitPulls(sha) {
      const { stdout } = await execFile('gh', [
        'api', `repos/${ghRepo}/commits/${sha}/pulls`,
      ], { maxBuffer: 16 * 1024 * 1024 });
      return JSON.parse(stdout);
    },
  };
}

function revertedPrNumber(title, message) {
  const text = `${title}\n${message}`;
  if (!/revert/i.test(text)) return null;
  const match = /revert(?:s|ed)?(?:\s+(?:pull request|pr))?\s+#(\d+)/i.exec(text);
  return match === null ? null : Number(match[1]);
}

async function blamedLinesForFix(repo, preFixSha, fixFiles) {
  const results = [];
  for (const file of fixFiles) {
    const deleted = file.lines.filter((line) => line.type === 'delete' && !isIgnorableBlameContent(line.content));
    if (deleted.length === 0 || file.oldPath === '/dev/null') continue;
    for (const range of coalesceRanges(deleted.map((line) => line.oldLine))) {
      const output = await git(repo, 'blame', '--porcelain', preFixSha, '-L', `${range[0]},${range[1]}`, '--', file.oldPath);
      for (const blame of parseBlamePorcelain(output)) {
        if (!isIgnorableBlameContent(blame.content)) {
          results.push({ file: file.oldPath, ...blame });
        }
      }
    }
  }
  return results;
}

/**
 * Mines fix/culprit pairs using injected GitHub metadata and read-only Git commands.
 *
 * @param {{repo: string, base: string, days: number, limit: number, maxFixLines: number, minCulpritLines: number, maxCulpritLines: number, metadata?: ReturnType<typeof metadataSource>}} options miner settings
 * @returns {Promise<{schemaVersion: 1, source: {repo: string, base: string, minedAt: string}, pairs: Array<object>}>} corpus payload
 */
export async function mineFixPairs(options) {
  const metadata = options.metadata ?? metadataSource(options.ghRepo);
  const fixes = await metadata.listFixPrs({ days: options.days, limit: options.limit });
  const pairs = [];

  for (const fix of fixes) {
    if (!/^fix(?:\(|:)/i.test(fix.title)) continue;
    let fixDetail;
    try {
      fixDetail = await metadata.getPullRequest(fix.number);
    } catch {
      continue;
    }
    if (changedLines(fixDetail) > options.maxFixLines) continue;
    const mergeCommit = typeof fix.mergeCommit === 'string' ? fix.mergeCommit : fix.mergeCommit?.oid;
    if (typeof mergeCommit !== 'string') continue;
    const reachesBase = await git(options.repo, 'merge-base', '--is-ancestor', mergeCommit, options.base)
      .then(() => true)
      .catch(() => false);
    if (!reachesBase) continue;
    const preFixSha = (await git(options.repo, 'rev-parse', `${mergeCommit}^1`)).trim();
    const message = await git(options.repo, 'log', '-1', '--format=%B', mergeCommit);
    const fixFiles = parseUnifiedDiff(await git(options.repo, 'diff', `${preFixSha}..${mergeCommit}`));
    const blameLines = await blamedLinesForFix(options.repo, preFixSha, fixFiles);
    const directCulprit = revertedPrNumber(fix.title, message);
    const prBySha = new Map();

    if (directCulprit !== null) {
      prBySha.set('revert', directCulprit);
    } else {
      for (const sha of new Set(blameLines.map((line) => line.sha))) {
        const associated = await metadata.getCommitPulls(sha);
        if (associated[0] !== undefined) prBySha.set(sha, associated[0].number);
      }
    }

    const distinctPrs = [...new Set(prBySha.values())];
    for (const culpritPrNumber of distinctPrs) {
      const culprit = await metadata.getPullRequest(culpritPrNumber);
      if (culprit.state !== 'MERGED') continue;
      const culpritChangedLines = changedLines(culprit);
      if (culpritChangedLines < options.minCulpritLines || culpritChangedLines > options.maxCulpritLines) continue;
      const isRevert = directCulprit === culpritPrNumber;
      const attributed = isRevert
        ? blameLines
        : blameLines.filter((line) => prBySha.get(line.sha) === culpritPrNumber);
      if (typeof culprit.mergeCommitSha !== 'string' || culprit.mergeCommitSha === '') {
        console.error(`Skipping culprit PR #${culpritPrNumber}: merge_commit_sha is unavailable`);
        continue;
      }
      if (!await hasCommit(options.repo, culprit.mergeCommitSha)) {
        console.error(`Skipping culprit PR #${culpritPrNumber}: merge commit ${culprit.mergeCommitSha} is not local`);
        continue;
      }
      let culpritBaseSha;
      try {
        culpritBaseSha = (await git(options.repo, 'rev-parse', `${culprit.mergeCommitSha}^1`)).trim();
      } catch {
        console.error(`Skipping culprit PR #${culpritPrNumber}: merge commit has no first parent`);
        continue;
      }
      if (!await hasCommit(options.repo, culpritBaseSha)) {
        console.error(`Skipping culprit PR #${culpritPrNumber}: first parent ${culpritBaseSha} is not local`);
        continue;
      }
      const culpritFiles = parseUnifiedDiff(await git(
        options.repo, 'diff', `${culpritBaseSha}..${culprit.mergeCommitSha}`,
      ));
      const regions = findDefectRegions(attributed, culpritFiles);
      const pair = {
        fixPr: fix.number,
        culpritPr: culpritPrNumber,
        culpritBaseSha,
        culpritHeadSha: culprit.mergeCommitSha,
        confidence: assignConfidence({
          isRevert,
          culpritPrCount: distinctPrs.length,
          resolvedCount: regions.resolvedCount,
          totalCount: attributed.length,
        }),
        changedFiles: [...new Set(fixFiles.map((file) => file.newPath === '/dev/null' ? file.oldPath : file.newPath))],
        defectLines: regions.defectLines,
        culpritChangedLines,
        sizeClass: culpritChangedLines >= 1000 ? 'large' : 'medium',
        fixTitle: fix.title,
        culpritTitle: culprit.title,
      };
      options.onPair?.({
        fixPr: pair.fixPr,
        culpritPr: pair.culpritPr,
        fixTitle: pair.fixTitle,
        culpritTitle: pair.culpritTitle,
        sampleLines: attributed.slice(0, 3).map((line) => normalizeContent(line.content)),
      });
      pairs.push(pair);
    }
  }

  return {
    schemaVersion: 1,
    source: { repo: 'local-clone', base: options.base, minedAt: new Date().toISOString() },
    pairs: pairs.map((pair, index) => {
      const { fixTitle, culpritTitle, ...corpusPair } = pair;
      return { id: `fp-${String(index + 1).padStart(4, '0')}`, ...corpusPair };
    }),
  };
}

export function parseArgs(argv) {
  const defaults = {
    repo: process.cwd(), base: 'origin/dev', days: 120, maxFixLines: 1500,
    minCulpritLines: 150, maxCulpritLines: 8000, limit: 25, ghRepo: '',
    out: 'tmp/fixpairs/corpus.json', sheet: 'tmp/fixpairs/review-sheet.md',
  };
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (value === undefined || !flag.startsWith('--')) throw new Error(`Expected --flag value, got ${flag ?? ''}`);
    const key = flag.slice(2).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    if (!(key in defaults)) throw new Error(`Unknown flag: ${flag}`);
    if (['days', 'maxFixLines', 'minCulpritLines', 'maxCulpritLines', 'limit'].includes(key)) {
      const number = Number(value);
      if (!Number.isFinite(number) || !Number.isInteger(number) || number < 0) {
        throw new Error(`${flag} must be a finite non-negative integer`);
      }
      defaults[key] = number;
    } else {
      defaults[key] = value;
    }
  }
  return defaults;
}

function assertOutputPath(output, explicitlyOverridden) {
  const outputRoot = resolve(process.cwd());
  const resolvedOutput = resolve(output);
  const allowed = ['tmp', 'evals/runs', 'evals/results'].some((directory) => {
    const root = resolve(outputRoot, directory);
    return resolvedOutput === root || resolvedOutput.startsWith(`${root}${sep}`);
  });
  if (!allowed && !explicitlyOverridden) {
    throw new Error(`Refusing to write private corpus outside gitignored paths: ${resolvedOutput}`);
  }
  if (!allowed) {
    console.error(`Privacy note: writing private identifiers outside gitignored paths: ${resolvedOutput}`);
  }
  return resolvedOutput;
}

function markdownSheet(corpus, details) {
  const rows = corpus.pairs.map((pair) => {
    const detail = details.get(`${pair.fixPr}:${pair.culpritPr}`);
    const samples = detail?.sampleLines.join('<br>') ?? '';
    return `| ${pair.id} | ${pair.confidence} | #${pair.fixPr} ${detail?.fixTitle ?? ''} | #${pair.culpritPr} ${detail?.culpritTitle ?? ''} | ${pair.defectLines.map((line) => line.file).join(', ')} | ${samples} |`;
  });
  return ['| Pair | Confidence | Fix PR | Culprit PR | Defect files | Sample normalized defect lines |', '| --- | --- | --- | --- | --- | --- |', ...rows, ''].join('\n');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const explicitOut = process.argv.slice(2).includes('--out');
  const out = assertOutputPath(args.out, explicitOut);
  const sheet = assertOutputPath(args.sheet, false);
  await git(args.repo, 'fetch', 'origin');
  const details = new Map();
  const corpus = await mineFixPairs({
    ...args,
    onPair: (detail) => details.set(`${detail.fixPr}:${detail.culpritPr}`, detail),
  });
  await mkdir(resolve(out, '..'), { recursive: true });
  await mkdir(resolve(sheet, '..'), { recursive: true });
  await writeFile(out, `${JSON.stringify(corpus, null, 2)}\n`);
  await writeFile(sheet, markdownSheet(corpus, details));
  console.log(`Mined ${corpus.pairs.length} fix pairs to ${out}`);
  console.log(`Wrote review sheet to ${sheet}`);
}

if (import.meta.main) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
