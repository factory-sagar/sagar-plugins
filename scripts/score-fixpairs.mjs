#!/usr/bin/env node
// Score fix-pair review findings against culprit-added-line regions.

import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

function normalizePath(filePath) {
  if (typeof filePath !== 'string') return null;
  let normalized = filePath.replaceAll('\\', '/');
  while (normalized.startsWith('./')) normalized = normalized.slice(2);
  return normalized;
}

function modelKey(run) {
  return `${run.model}@${run.effort ?? 'default'}`;
}

/**
 * Classify one finding against a labeled fix-pair's defect regions.
 *
 * @param {object} pair Fix-pair corpus record.
 * @param {object} finding Review finding record.
 * @returns {'regionHit' | 'nearMiss' | 'outsideRegions' | 'unlocated'} Location bucket.
 */
export function classifyFinding(pair, finding) {
  const findingPath = normalizePath(finding.path);
  if (findingPath === null) return 'unlocated';

  const defectLine = pair.defectLines.find(
    (entry) => normalizePath(entry.file) === findingPath,
  );
  if (defectLine) {
    const lineIsInRegion = Number.isInteger(finding.line)
      && defectLine.culpritAddedLines.some(
        ([start, end]) => finding.line >= start && finding.line <= end,
      );
    return lineIsInRegion ? 'regionHit' : 'nearMiss';
  }

  const isChangedFile = pair.changedFiles.some(
    (changedFile) => normalizePath(changedFile) === findingPath,
  );
  return isChangedFile ? 'nearMiss' : 'outsideRegions';
}

/**
 * Return the median of numeric values, or zero when no measurements exist.
 *
 * @param {number[]} values Numeric measurements.
 * @returns {number} Median measurement.
 */
export function median(values) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}

function createAggregate() {
  return {
    pairs: new Set(),
    pairHits: new Set(),
    regionHits: 0,
    nearMisses: 0,
    outsideRegions: 0,
    unlocated: 0,
    findingsTotal: 0,
    runs: 0,
    erroredRuns: 0,
    credits: [],
    durations: [],
  };
}

function createPairAggregate(pair, key) {
  return {
    pairId: pair.id,
    confidence: pair.confidence,
    model: key,
    hit: false,
    regionHits: 0,
    nearMisses: 0,
    outsideRegions: 0,
    unlocated: 0,
    runs: 0,
  };
}

function aggregateBucket(bucket) {
  return bucket === 'regionHit' ? 'regionHits' : bucket === 'nearMiss' ? 'nearMisses' : bucket;
}

function publicAggregate(aggregate) {
  const pairsScored = aggregate.pairs.size;
  const pairHits = aggregate.pairHits.size;
  return {
    pairsScored,
    pairHits,
    pairHitRate: pairsScored === 0 ? 0 : pairHits / pairsScored,
    regionHits: aggregate.regionHits,
    nearMisses: aggregate.nearMisses,
    outsideRegions: aggregate.outsideRegions,
    unlocated: aggregate.unlocated,
    findingsTotal: aggregate.findingsTotal,
    runs: aggregate.runs,
    erroredRuns: aggregate.erroredRuns,
    creditsTotal: aggregate.credits.reduce((total, credits) => total + credits, 0),
    creditsMedianPerRun: median(aggregate.credits),
    durationMsMedianPerRun: median(aggregate.durations),
  };
}

/**
 * Score review runs using only the labeled regions from a fix-pair corpus.
 * Errored runs contribute only to their aggregate's `erroredRuns` count.
 *
 * @param {object} corpus Parsed fix-pair corpus.
 * @param {object[]} runs Parsed review run findings.
 * @returns {object} Privacy-safe score data without timestamps or finding text.
 */
export function scoreFixPairs(corpus, runs) {
  const pairsById = new Map(corpus.pairs.map((pair) => [pair.id, pair]));
  const roleAggregates = new Map();
  const pairAggregates = new Map();

  for (const run of runs) {
    const pair = pairsById.get(run.pairId);
    if (!pair) {
      throw new Error(`run references unknown corpus pair: ${run.pairId}`);
    }

    const key = modelKey(run);
    const aggregateKey = `${run.role}\u0000${key}`;
    let aggregate = roleAggregates.get(aggregateKey);
    if (!aggregate) {
      aggregate = { role: run.role, model: key, values: createAggregate() };
      roleAggregates.set(aggregateKey, aggregate);
    }

    if (run.error !== null) {
      aggregate.values.erroredRuns += 1;
      continue;
    }

    const pairAggregateKey = `${run.role}\u0000${key}\u0000${pair.id}`;
    let perPair = pairAggregates.get(pairAggregateKey);
    if (!perPair) {
      perPair = createPairAggregate(pair, key);
      pairAggregates.set(pairAggregateKey, perPair);
    }

    aggregate.values.pairs.add(pair.id);
    aggregate.values.runs += 1;
    aggregate.values.credits.push(run.usage.factory_credits);
    aggregate.values.durations.push(run.durationMs);
    perPair.runs += 1;

    for (const finding of run.findings) {
      const bucket = aggregateBucket(classifyFinding(pair, finding));
      aggregate.values[bucket] += 1;
      aggregate.values.findingsTotal += 1;
      perPair[bucket] += 1;
    }

    if (perPair.regionHits > 0) {
      perPair.hit = true;
      aggregate.values.pairHits.add(pair.id);
    }
  }

  const roles = {};
  for (const aggregate of [...roleAggregates.values()].sort((left, right) =>
    left.role.localeCompare(right.role) || left.model.localeCompare(right.model),
  )) {
    roles[aggregate.role] ??= { models: {}, perPair: [] };
    roles[aggregate.role].models[aggregate.model] = publicAggregate(aggregate.values);
  }

  for (const [aggregateKey, perPair] of pairAggregates) {
    const [role] = aggregateKey.split('\u0000');
    roles[role].perPair.push(perPair);
  }
  for (const role of Object.values(roles)) {
    role.perPair.sort(
      (left, right) => left.pairId.localeCompare(right.pairId)
        || left.model.localeCompare(right.model),
    );
  }

  return {
    schemaVersion: 1,
    corpusPairs: corpus.pairs.length,
    roles,
  };
}

/**
 * Format aggregate scores as a Markdown table suitable for terminal output.
 *
 * @param {object} scores Score data from {@link scoreFixPairs}.
 * @returns {string} Markdown summary table.
 */
export function formatMarkdownSummary(scores) {
  const lines = [
    '| Role | Model | Pairs scored | Pair hits | Pair hit rate | Region hits | Near misses | Outside regions | Unlocated | Findings | Runs | Errored runs | Credits total | Credits median/run | Duration median/run (ms) |',
    '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
  ];

  for (const [roleName, role] of Object.entries(scores.roles)) {
    for (const [model, aggregate] of Object.entries(role.models)) {
      lines.push(
        `| ${roleName} | ${model} | ${aggregate.pairsScored} | ${aggregate.pairHits} | ${(aggregate.pairHitRate * 100).toFixed(1)}% | ${aggregate.regionHits} | ${aggregate.nearMisses} | ${aggregate.outsideRegions} | ${aggregate.unlocated} | ${aggregate.findingsTotal} | ${aggregate.runs} | ${aggregate.erroredRuns} | ${aggregate.creditsTotal} | ${aggregate.creditsMedianPerRun} | ${aggregate.durationMsMedianPerRun} |`,
      );
    }
  }
  return lines.join('\n');
}

/**
 * Persist privacy-safe scores, creating the destination directory when needed.
 *
 * @param {string} outputFile Scores output path.
 * @param {object} scores Score data from {@link scoreFixPairs}.
 * @param {string} [generatedAt] ISO timestamp for reproducible tests.
 */
export function writeScores(outputFile, scores, generatedAt = new Date().toISOString()) {
  mkdirSync(path.dirname(outputFile), { recursive: true });
  writeFileSync(
    outputFile,
    `${JSON.stringify({
      schemaVersion: 1,
      generatedAt,
      corpusPairs: scores.corpusPairs,
      roles: scores.roles,
    }, null, 2)}\n`,
  );
}

function hasGlob(pattern) {
  return /[*?[]/.test(pattern);
}

function globExpression(pattern) {
  let expression = '^';
  for (let index = 0; index < pattern.length; index += 1) {
    const character = pattern[index];
    if (character === '*') {
      if (pattern[index + 1] === '*') {
        index += 1;
        if (pattern[index + 1] === '/') {
          index += 1;
          expression += '(?:.*/)?';
        } else {
          expression += '.*';
        }
      } else {
        expression += '[^/]*';
      }
    } else if (character === '?') {
      expression += '[^/]';
    } else if (character === '[') {
      const closingIndex = pattern.indexOf(']', index + 1);
      if (closingIndex === -1) {
        expression += '\\[';
      } else {
        const classContents = pattern.slice(index + 1, closingIndex);
        if (classContents.length === 0 || classContents.includes('/')) {
          expression += '\\[';
        } else {
          const negated = classContents.startsWith('!') ? '^' : '';
          const characters = (negated ? classContents.slice(1) : classContents)
            .replaceAll('\\', '\\\\')
            .replaceAll(']', '\\]');
          expression += `[${negated}${characters}]`;
          index = closingIndex;
        }
      }
    } else {
      expression += character.replace(/[|\\{}()[\]^$+?.]/g, '\\$&');
    }
  }
  return new RegExp(`${expression}$`);
}

function staticGlobRoot(absolutePattern) {
  const parts = absolutePattern.split('/');
  const fixedParts = [];
  for (const part of parts) {
    if (hasGlob(part)) break;
    fixedParts.push(part);
  }
  const fixedPath = fixedParts.join('/') || '/';
  return fixedParts.length === parts.length ? path.dirname(fixedPath) : fixedPath;
}

function filesUnder(directory) {
  if (!existsSync(directory)) return [];
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...filesUnder(file));
    } else if (entry.isFile()) {
      files.push(file);
    }
  }
  return files;
}

/**
 * Expand quoted filesystem glob patterns without relying on the invoking shell.
 *
 * @param {string[]} inputs Explicit paths or glob patterns.
 * @returns {string[]} Sorted unique findings file paths.
 */
export function expandFindingPaths(inputs) {
  const matches = new Set();
  for (const input of inputs) {
    const absolute = path.resolve(input);
    if (!hasGlob(absolute)) {
      if (!existsSync(absolute)) throw new Error(`missing findings file: ${input}`);
      matches.add(absolute);
      continue;
    }

    const matcher = globExpression(absolute.replaceAll('\\', '/'));
    for (const file of filesUnder(staticGlobRoot(absolute))) {
      if (matcher.test(file.replaceAll('\\', '/'))) matches.add(file);
    }
  }
  return [...matches].sort();
}

function usage() {
  return 'usage: score-fixpairs.mjs --corpus <corpus.json> --runs <findings.json|glob> [<findings.json|glob>...] [--out <scores.json>]';
}

function parseArguments(arguments_) {
  let corpusFile;
  let outputFile;
  const runInputs = [];
  for (let index = 0; index < arguments_.length; index += 1) {
    const argument = arguments_[index];
    if (argument === '--corpus' || argument === '--out') {
      const value = arguments_[index + 1];
      if (!value || value.startsWith('--')) throw new Error(`missing value for ${argument}`);
      if (argument === '--corpus') corpusFile = value;
      else outputFile = value;
      index += 1;
    } else if (argument === '--runs') {
      while (arguments_[index + 1] && !arguments_[index + 1].startsWith('--')) {
        runInputs.push(arguments_[index + 1]);
        index += 1;
      }
    } else {
      throw new Error(`unknown argument: ${argument}`);
    }
  }
  if (!corpusFile || runInputs.length === 0) throw new Error('both --corpus and --runs are required');
  return { corpusFile, runInputs, outputFile };
}

function main() {
  try {
    const { corpusFile, runInputs, outputFile } = parseArguments(process.argv.slice(2));
    const corpus = JSON.parse(readFileSync(corpusFile, 'utf8'));
    const findingFiles = expandFindingPaths(runInputs);
    if (findingFiles.length === 0) throw new Error('no findings files matched --runs inputs');
    const runs = findingFiles.map((file) => JSON.parse(readFileSync(file, 'utf8')));
    const scores = scoreFixPairs(corpus, runs);
    console.log(formatMarkdownSummary(scores));
    if (outputFile) writeScores(outputFile, scores);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    console.error(usage());
    process.exitCode = 2;
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  main();
}
