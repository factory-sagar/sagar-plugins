# Behavior

Given ordered commands, searching returns only enabled matching commands, ranks case-insensitive prefix matches above substring matches, and preserves input order within equal match ranks.

# Standards Loaded

- `tdd-workflow/SKILL.md`
- `coding-standards/SKILL.md`
- `TESTING_AND_VERIFICATION.md`
- `DESIGNING_MODULES.md`
- `TYPE_CONTRACTS.md`

# RED/GREEN Slices

1. **Ranking and stability**
   - RED: `cb992da`, 2 tests failed with `Error: not implemented`.
   - GREEN: `b10e20f`, grouped prefix and substring matches while preserving encounter order. Targeted suite: 2 passing.

2. **Disabled commands**
   - RED: `a1de5bd`, disabled-command test failed because disabled prefix and substring commands were returned.
   - GREEN: `efcee3c`, skips `disabled` commands before matching. Targeted suite: 3 passing.

# Validation Evidence

- `npm --prefix ".../golden-06-tdd-workflow-plan.9LSGUb" test`
  - **3 passed, 0 failed**, duration `51.985042ms`.
- `node --test --experimental-test-coverage ".../src/command-palette.test.mjs"`
  - **3 passed, 0 failed**
  - `src/command-palette.mjs`: **100% line, branch, and function coverage**.
- `git diff --check 7bbb134..HEAD`: passed.
- Working tree is clean on `main`.

Deviations: TDD steps were performed inline as explicitly required.
