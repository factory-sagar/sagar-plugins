# Command Palette Suggestions

## Behavior Statement
Given commands and a query, when users search the palette, enabled prefix matches appear before enabled substring matches, while equal match classes retain command order.

## Standards Loaded
- `coding-standards/SKILL.md`
- `TESTING_AND_VERIFICATION.md`
- `DESIGNING_MODULES.md`
- `TYPE_CONTRACTS.md`

## RED/GREEN Slices
1. **Prefix suggestions**
   - RED `3c29d2b`: 2 failing tests, placeholder throws `not implemented`.
   - GREEN `bc945ac`: 2 passing tests.

2. **Prefix ranking, substring matches, stable ordering**
   - RED `7c6d1e2`: assertion failure, substring matches were omitted.
   - GREEN `bb4a1b4`: 3 passing tests.

3. **Disabled commands**
   - RED `b76ca59`: assertion failure, disabled prefix and substring matches were included.
   - GREEN `37e9116`: 4 passing tests.

## Validation Evidence
- `npm test`: **4 passed, 0 failed**
- `node --test --experimental-test-coverage`: **100% line, branch, and function coverage** for `src/command-palette.mjs`
- `git diff --check`: passed
- All RED/GREEN commits are reachable from `HEAD`.
- Working tree is clean.
