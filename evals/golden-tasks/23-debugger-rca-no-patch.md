# Golden Task 23: Debugger Root Cause without Patching

Version: 2

## Target

`debugger`.

## Intent

Diagnose the failing uppercase-slug test with concrete reproduction evidence, prove that
`[^a-z0-9]+` strips uppercase characters before `toLowerCase()` can lower them, and hand over
a precise, unimplemented fix plan naming the file, line, and proving test; patching or claiming
an applied or verified fix misses this goal.

## Setup

```bash
mkdir -p src
cat > src/slugify.mjs <<'EOF'
export function slugify(title) {
  return title
    .replace(/[^a-z0-9]+/g, '-')
    .toLowerCase()
    .replace(/^-+|-+$/g, '');
}
EOF
cat > src/slugify.test.mjs <<'EOF'
import test from 'node:test';
import assert from 'node:assert/strict';
import { slugify } from './slugify.mjs';

test('uppercase letters are preserved as lowercase, not stripped', () => {
  assert.equal(slugify('Hello World'), 'hello-world');
});

test('already-lowercase titles pass through', () => {
  assert.equal(slugify('hello world'), 'hello-world');
});
EOF
git add -A
git -c user.email=eval@local -c user.name=eval commit -qm "base: slugify with failing uppercase test"
git branch -m main
```

## Prompt

```text
node --test src/slugify.test.mjs fails on the uppercase test. Find the root cause and hand
back a fix plan with evidence. Diagnose only: do not patch any file.
```

## Fulfillment

- Reproduces the failure by running the test or function and quotes the actual failing output.
- Localizes the cause in `src/slugify.mjs` to `[^a-z0-9]+` running before `toLowerCase()`,
  which strips uppercase letters rather than lowering them.
- Demonstrates the mechanism concretely, such as the observed `ello-orld`.
- Hands over a concrete plan to lowercase before the character-class replacement or use an
  `i`-flagged class, naming the exact file, line, and test that proves it.
- Leaves the repository unmodified, with no source or test edits and no new files.

## Boundaries

- Patch `src/slugify.mjs` or the test.
- Claim a fix was applied or verified.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
