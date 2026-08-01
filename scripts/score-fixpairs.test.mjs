import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  classifyFinding,
  expandFindingPaths,
  formatMarkdownSummary,
  median,
  scoreFixPairs,
  writeScores,
} from './score-fixpairs.mjs';

const corpus = {
  schemaVersion: 1,
  pairs: [
    {
      id: 'fp-0001',
      confidence: 'high',
      changedFiles: ['src/target.js', 'src/changed-only.js'],
      defectLines: [
        {
          file: 'src/target.js',
          culpritAddedLines: [[10, 12]],
        },
      ],
    },
  ],
};

function run(overrides = {}) {
  return {
    schemaVersion: 1,
    pairId: 'fp-0001',
    role: 'change-review',
    model: 'model-a',
    effort: null,
    rep: 1,
    durationMs: 100,
    usage: {
      factory_credits: 10,
      input_tokens: 20,
      output_tokens: 30,
    },
    findings: [],
    error: null,
    ...overrides,
  };
}

test('classifyFinding normalizes paths and separates all location buckets', () => {
  const pair = corpus.pairs[0];

  assert.equal(
    classifyFinding(pair, { path: './src/target.js', line: 11 }),
    'regionHit',
  );
  assert.equal(
    classifyFinding(pair, { path: 'src/target.js', line: 13 }),
    'nearMiss',
  );
  assert.equal(
    classifyFinding(pair, { path: './src/changed-only.js', line: 1 }),
    'nearMiss',
  );
  assert.equal(
    classifyFinding(pair, { path: 'src/unrelated.js', line: 1 }),
    'outsideRegions',
  );
  assert.equal(
    classifyFinding(pair, { path: null, line: 1 }),
    'unlocated',
  );
});

test('scoreFixPairs excludes errored runs and deduplicates a pair hit across reps', () => {
  const scores = scoreFixPairs(corpus, [
    run({
      findings: [
        { title: 'hit', path: './src/target.js', line: 10 },
        { title: 'near defect', path: 'src/target.js', line: 99 },
        { title: 'near changed', path: 'src/changed-only.js', line: 1 },
        { title: 'outside', path: 'src/elsewhere.js', line: 1 },
        { title: 'unlocated', path: null, line: 0 },
      ],
    }),
    run({
      rep: 2,
      durationMs: 300,
      usage: { factory_credits: 30, input_tokens: 0, output_tokens: 0 },
      findings: [{ title: 'second hit', path: 'src/target.js', line: 12 }],
    }),
    run({
      rep: 3,
      error: 'runner failed',
      durationMs: 900,
      usage: { factory_credits: 90, input_tokens: 0, output_tokens: 0 },
      findings: [{ title: 'must not count', path: 'src/target.js', line: 10 }],
    }),
  ]);

  const model = scores.roles['change-review'].models['model-a@default'];
  assert.deepEqual(model, {
    pairsScored: 1,
    pairHits: 1,
    pairHitRate: 1,
    regionHits: 2,
    nearMisses: 2,
    outsideRegions: 1,
    unlocated: 1,
    findingsTotal: 6,
    runs: 2,
    erroredRuns: 1,
    creditsTotal: 40,
    creditsMedianPerRun: 20,
    durationMsMedianPerRun: 200,
  });
  assert.deepEqual(scores.roles['change-review'].perPair, [
    {
      pairId: 'fp-0001',
      confidence: 'high',
      model: 'model-a@default',
      hit: true,
      regionHits: 2,
      nearMisses: 2,
      outsideRegions: 1,
      unlocated: 1,
      runs: 2,
    },
  ]);
});

test('median calculates odd, even, and empty samples', () => {
  assert.equal(median([]), 0);
  assert.equal(median([5]), 5);
  assert.equal(median([9, 1, 5]), 5);
  assert.equal(median([30, 10]), 20);
});

test('expandFindingPaths supports bracket-class quoted globs', () => {
  const directory = mkdtempSync(path.join(os.tmpdir(), 'score-fixpairs-glob-'));
  const one = path.join(directory, 'run-1', 'findings.json');
  const two = path.join(directory, 'run-2', 'findings.json');

  try {
    mkdirSync(path.dirname(one), { recursive: true });
    mkdirSync(path.dirname(two), { recursive: true });
    writeFileSync(one, '{}');
    writeFileSync(two, '{}');
    assert.deepEqual(
      expandFindingPaths([path.join(directory, 'run-[12]', 'findings.json')]),
      [one, two],
    );
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('scores are private and the markdown table summarizes two models', () => {
  const scores = scoreFixPairs(corpus, [
    run({
      findings: [{ title: 'factory-mono 0123456789abcdef0123456789abcdef01234567', path: 'src/target.js', line: 10 }],
    }),
    run({
      model: 'model-b',
      effort: 'high',
      durationMs: 200,
      usage: { factory_credits: 20, input_tokens: 0, output_tokens: 0 },
    }),
  ]);
  const directory = mkdtempSync(path.join(os.tmpdir(), 'score-fixpairs-'));
  const output = path.join(directory, 'scores.json');

  try {
    writeScores(output, scores, '2026-07-30T00:00:00.000Z');
    const serialized = readFileSync(output, 'utf8');
    assert.doesNotMatch(serialized, /title/i);
    assert.doesNotMatch(serialized, /\b[0-9a-f]{40}\b/i);
    assert.doesNotMatch(serialized, /factory-mono/i);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }

  assert.equal(
    formatMarkdownSummary(scores),
    [
      '| Role | Model | Pairs scored | Pair hits | Pair hit rate | Region hits | Near misses | Outside regions | Unlocated | Findings | Runs | Errored runs | Credits total | Credits median/run | Duration median/run (ms) |',
      '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
      '| change-review | model-a@default | 1 | 1 | 100.0% | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 10 | 10 | 100 |',
      '| change-review | model-b@high | 1 | 0 | 0.0% | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 20 | 20 | 200 |',
    ].join('\n'),
  );
});
