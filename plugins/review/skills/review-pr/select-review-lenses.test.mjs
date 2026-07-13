import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  REVIEW_LENSES,
  selectReviewLenses,
} from './select-review-lenses.mjs';

const ids = (result) => result.map(({ id }) => id);

test('always includes the mandatory policy', () => {
  assert.deepEqual(ids(selectReviewLenses({ paths: ['src/math.py'], diff: '+return a + b' })), [
    'mandatory',
  ]);
});

test('selects reactivity by behavior rather than language', () => {
  const reactResult = selectReviewLenses({
    paths: ['src/Panel.tsx'],
    diff: '+useEffect(() => subscribe(store), [store]);',
  });
  const react = ids(reactResult);
  const vue = ids(selectReviewLenses({
    paths: ['src/Panel.vue'],
    diff: '+watch(selection, () => refresh());',
  }));

  assert.ok(react.includes('ui-state-reactivity'));
  assert.ok(vue.includes('ui-state-reactivity'));
  const uiLens = reactResult.find(({ id }) => id === 'ui-state-reactivity');
  assert.deepEqual(uiLens.evidenceRequirements, [
    'trace the real initiating owner and every programmatic writer',
    'follow retained state through the terminal transition event',
    'prove precedence where selectors or declarative rules overlap',
  ]);
});

test('selects mutation, input, auth, and persistence lenses together', () => {
  const result = ids(selectReviewLenses({
    paths: ['backend/migrations/004_add_members.sql', 'backend/routes/members.py'],
    diff: [
      '+org_id = request.query["orgId"]',
      '+members.append(await store.find_user(org_id))',
      '+UPDATE memberships SET role = ${role}',
    ].join('\n'),
  }));

  assert.ok(result.includes('mutation-state-ownership'));
  assert.ok(result.includes('authentication-authorization'));
  assert.ok(result.includes('external-input-injection'));
  assert.ok(result.includes('persistence-migration'));
  assert.ok(result.includes('async-concurrency'));
});

test('selects supply-chain and delivery lenses from repository surfaces', () => {
  const result = ids(selectReviewLenses({
    paths: ['package-lock.json', '.github/workflows/release.yml', 'Dockerfile'],
    diff: '+      run: npm install && npm run deploy',
  }));

  assert.ok(result.includes('dependencies-supply-chain'));
  assert.ok(result.includes('ci-build-release'));
});

test('selects agentic configuration without unrelated language lenses', () => {
  const result = ids(selectReviewLenses({
    paths: ['plugins/review/skills/review-pr/SKILL.md', 'hooks/stop-gate.py'],
    diff: '+description: Review a pull request',
  }));

  assert.ok(result.includes('agentic-configuration'));
  assert.ok(!result.includes('ui-state-reactivity'));
  assert.ok(!result.includes('persistence-migration'));
});

test('returns stable ordering and evidence for every selected lens', () => {
  const result = selectReviewLenses({
    paths: ['src/auth/session.ts'],
    diff: '+const token = request.headers.authorization;\n+logger.info(token);',
  });

  assert.deepEqual(ids(result), [
    'mandatory',
    'authentication-authorization',
    'external-input-injection',
    'secrets-privacy-observability',
    'public-contracts-compatibility',
  ]);
  assert.ok(result.every(({ signal }) => typeof signal === 'string' && signal.length > 0));
});

test('every selector lens points to a real policy section', () => {
  const policy = readFileSync(new URL('./review-policy.md', import.meta.url), 'utf8');
  for (const lens of REVIEW_LENSES) {
    assert.ok(policy.includes(lens.policySection), lens.policySection);
    assert.ok(['change-review', 'security'].includes(lens.reviewer), lens.reviewer);
  }
});
