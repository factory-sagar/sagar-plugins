# Debugger

## Summary

The uppercase test fails because uppercase characters are removed before lowercasing. **Confidence: high.**

## Reproduction

- Command: `node --test src/slugify.test.mjs`
- Result: actual `'ello-orld'`, expected `'hello-world'`
- Determinism: deterministic

## Recent-Change Scan

Commit `1e48a59` introduced both implementation and test. No earlier working version exists.

## Hypotheses

| # | Hypothesis | Status | Evidence |
|---|---|---|---|
| 1 | Lowercasing occurs after a lowercase-only filter | confirmed | Filtering `"Hello World"` first produces `"-ello-orld"`; lowercasing first produces `"hello-world"` |

## Root Cause — High

- **Mechanism:** `src/slugify.mjs:3` uses `/[^a-z0-9]+/g` before `toLowerCase()`. Uppercase letters therefore match the forbidden-character class and become separators. Boundary trimming then removes the leading separator.
- **Causal chain:** `'ello-orld'` ← leading separator trimmed ← uppercase letters replaced ← lowercase-only filter runs before normalization.
- **Trigger vs cause:** Uppercase input triggers the defect; incorrect transformation ordering causes it.

This also predicts `fooBar → foo-ar` and `ABC → ''`, both confirmed.

## Fix Plan (for `implementer`)

1. `src/slugify.mjs:2-5` — move `.toLowerCase()` before the lowercase-only replacement, retaining separator collapsing and boundary trimming. Risk: verify punctuation and lowercase behavior remain unchanged.
2. Run `node --test src/slugify.test.mjs`.

## Pin-It Test (for `test-engineer`)

- Retain `src/slugify.test.mjs:5-7`, asserting `slugify('Hello World') === 'hello-world'`.

## Mitigation

- None.

## Prevention

- Cover transformation ordering with lowercase, mixed-case, and all-uppercase cases.

## Blocked-On

None. No files were changed; the source diff remains empty.

## Hand-off

- To `implementer`: apply the fix plan above.
- To `test-engineer`: preserve the existing regression test.
- To `review-pr`: none.
- To `deep-research` / `deep-understanding`: none.
