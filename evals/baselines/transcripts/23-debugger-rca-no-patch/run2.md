# Debugger

## Summary

The uppercase test fails deterministically because case-sensitive filtering runs before lowercase normalization. **Confidence: high.**

## Reproduction

- Command: `node --test --test-name-pattern='uppercase letters' src/slugify.test.mjs`
- Result:

```text
actual:   'ello-orld'
expected: 'hello-world'
tests 1, pass 0, fail 1
```

- Determinism: deterministic

## Recent-Change Scan

Commit `d5f0cbf` introduced both the implementation and failing test. There is no earlier implementation history to compare.

## Hypotheses

| # | Hypothesis | Status | Evidence |
|---|---|---|---|
| 1 | Uppercase characters are filtered before normalization | confirmed | The first replacement transforms `Hello World` into `-ello-orld`. |
| 2 | `toLowerCase()` is malfunctioning | eliminated | The uppercase characters are already absent before it runs; lowercase input passes. |
| 3 | Final hyphen trimming removes the initials | eliminated | Before trimming, the value is already `-ello-orld`. |
| 4 | Space-to-hyphen conversion is defective | eliminated | `hello world` correctly becomes `hello-world`. |

## Root Cause: High Confidence

- **Mechanism:** At `src/slugify.mjs:3`, the case-sensitive expression `/[^a-z0-9]+/g` treats `H` and `W` as invalid. They are replaced before `toLowerCase()` runs at line 4, so normalization cannot recover them.
- **Causal chain:** assertion failure ← `ello-orld` returned ← uppercase letters replaced as separators ← filtering precedes case normalization.
- **Trigger vs cause:** Mixed-case input triggers the defect; incorrect transformation ordering causes it.

## Fix Plan (for `implementer`)

1. `src/slugify.mjs:2-5`: move `.toLowerCase()` before the invalid-character replacement so ASCII uppercase letters enter the allowlist as lowercase. Risk: verify intended handling of non-ASCII case folding.
2. Run `node --test src/slugify.test.mjs` and confirm both tests pass.

## Pin-It Test (for `test-engineer`)

- Retain `src/slugify.test.mjs:5-7`, which covers uppercase characters at both word boundaries and asserts `Hello World` becomes `hello-world`.

## Mitigation

- None.

## Prevention

- Keep mixed-case and lowercase cases together as transformation-order regression coverage.

## Blocked-On

None.

## Hand-off

- To `implementer`: apply the ordering change above.
- To `test-engineer`: preserve the existing uppercase regression test.
- Other follow-ups: none.

No files were patched. `git diff --exit-code` passed; only the pre-existing untracked `.factory/` directory remains.
