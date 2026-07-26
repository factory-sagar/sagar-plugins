import assert from 'node:assert/strict';
import test from 'node:test';

import { routingDuplicationErrors } from './validate.mjs';

const marker = '<!-- routing-table:' + 'canonical -->';
const canonical = {
  file: 'docs/WORKFLOW.md',
  text: `${marker}\n| Intent | Type |\n| --- | --- |\n| Plan | \`/spec\` |\n| Build | \`/implement\` |\n| Review | \`/review-pr\` |\n| Ship | \`/ship\` |`,
};

test('accepts one canonical routing table', () => {
  assert.deepEqual(routingDuplicationErrors([canonical]), []);
});

test('reports duplicate cross-plugin routing tables with file and line', () => {
  assert.deepEqual(routingDuplicationErrors([
    canonical,
    {
      file: 'plugins/build/README.md',
      text: '# build\n\n| `/spec` | `/implement` | `/review-pr` | `/ship` |',
    },
  ]), [
    'plugins/build/README.md:3: duplicate cross-plugin routing table row names spec, implement, review-pr, ship',
  ]);
});

test('reports every file with a duplicate canonical marker', () => {
  assert.deepEqual(routingDuplicationErrors([
    canonical,
    { file: 'README.md', text: marker },
  ]), [
    'routing-table marker must appear in exactly one tracked Markdown file; found 2: docs/WORKFLOW.md, README.md',
  ]);
});
