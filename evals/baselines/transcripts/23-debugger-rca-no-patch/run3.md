# Debugger

## Summary

Uppercase characters are removed before lowercasing. Root cause confidence: **high**.

## Reproduction

- Command: `node --test src/slugify.test.mjs`
- Result: expected `hello-world`, received `ello-orld`
- Determinism: deterministic

## Recent-Change Scan

Commit `d139692` introduced both implementation and tests. No earlier history exists.

## Hypotheses

| # | Hypothesis | Status | Evidence |
|---|---|---|---|
| 1 | Sanitization occurs before lowercasing | confirmed | `"Hello World"` becomes `"-ello-orld"` after the first replacement. Lowercasing first produces `"hello-world"`. |

## Root Cause — High

- **Mechanism:** `src/slugify.mjs:3` permits only lowercase ASCII characters. It therefore replaces `H` and `W` before `toLowerCase()` runs on line 4. The removed characters cannot be recovered. All-uppercase input such as `"ABC"` consequently becomes an empty slug.
- **Causal chain:** `ello-orld` ← leading separator trimmed ← uppercase letters replaced with separators ← sanitization runs before normalization.
- **Trigger vs cause:** Uppercase input triggers the defect; incorrect transformation ordering causes it.

## Fix Plan (for `implementer`)

1. `src/slugify.mjs:2-4` — move `.toLowerCase()` before the character-filtering `.replace(...)`. Preserve separator collapsing and edge trimming. Risk: limited to intentionally retaining uppercase ASCII letters as lowercase.
2. Run `node --test src/slugify.test.mjs`; no test edit is required.

## Pin-It Test (for `test-engineer`)

- Retain `src/slugify.test.mjs:5-7`, which already asserts that `"Hello World"` becomes `"hello-world"`.

## Mitigation

- None.

## Prevention

- Keep the existing uppercase regression test in the permanent suite.

## Blocked-On

None.

## Hand-off

- To `implementer`: apply the ordering change above.
- To `test-engineer`: existing test already pins the defect.
- Other hand-offs: none.
- Repository files were not modified. `git diff` is clean; pre-existing untracked `.factory/` remains untouched.
- Deviations: none.
