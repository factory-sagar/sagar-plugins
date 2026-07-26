# Implemented

**Behavior:** Given commands and a query, return enabled matching commands with prefix matches before substring matches, preserving input order for equal scores.

# Standards Loaded

- `coding-standards/SKILL.md`
- `TESTING_AND_VERIFICATION.md`
- `DESIGNING_MODULES.md`
- `TYPE_CONTRACTS.md`

# TDD Evidence

1. **Prefix ranking**
   - RED: targeted test failed with `not implemented`.
   - GREEN: targeted test passed, `2/2`.
   - Commits: `f6318c9`, `8bc346c`.

2. **Disabled commands**
   - RED: targeted test failed because the disabled command was returned.
   - GREEN: targeted test passed, `3/3`.
   - Commits: `4728a3c`, `9128a7f`.

3. **Stable equal-score ordering**
   - Added a behavior test covering both equal prefix and equal substring scores.
   - GREEN immediately, `4/4`, because the existing zero-score comparator and runtime stable sort already preserved input ordering.
   - Commit: `2116fce`.

# Validation

```text
npm test
✔ tests 4
✔ pass 4
✔ fail 0
```

```text
git diff --check 6741c57..HEAD
# passed with no output
```

Working tree is clean.
