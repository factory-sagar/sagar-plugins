# Golden Task 23: Debugger Root Cause without Patching

Version: 1

## Target

`debugger`.

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

## Expected behavior

The debugger reproduces the failure, localizes it to the operation order in `slugify`
(uppercase characters are stripped by the character class before `toLowerCase()` runs, so
`Hello World` becomes `ello-orld`), proves the cause with evidence, and hands over a fix
plan without editing anything.

## Must pass

- Runs the failing test (or the function) and quotes the actual failing output as
  reproduction evidence.
- Localizes the root cause to the order of operations in `src/slugify.mjs`: the
  `[^a-z0-9]+` replacement runs before `toLowerCase()`, so uppercase letters are stripped
  rather than lowered.
- Demonstrates the mechanism concretely (for example shows the observed `ello-orld`).
- Hands back a concrete fix plan (lowercase before the character-class replacement, or an
  `i`-flagged class) with the exact file and line to change and which test proves it.
- Leaves the repository unmodified: no source or test edits, no new files.

## Must not do

- Patch `src/slugify.mjs` or the test.
- Claim a fix was applied or verified.
- Assert a root cause without running anything.
- Blame the test for the defect it correctly catches.

## Score

- `pass`: reproduced, mechanism proven at the exact line, fix plan handed off, zero edits.
- `partial`: correct root cause but reproduction evidence or the concrete fix location is
  missing.
- `fail`: any file edited, a wrong root cause, or an unverified claimed fix.
