# Command Palette Suggestions

**Behavior:** Given commands and a query, return enabled matches with prefix matches before substring matches, preserving source order for equal scores.

## Standards Loaded
- `coding-standards/SKILL.md`
- `TESTING_AND_VERIFICATION.md`
- `DESIGNING_MODULES.md`
- `TYPE_CONTRACTS.md`

## TDD Slices
1. **RED:** prefix/substrings and stable ordering, `2` failures with `Error: not implemented`.  
   **GREEN:** prefix ranking, stable ordering, and case-insensitive matching, `2` passing.
2. **RED:** disabled matching command exclusion, `1` assertion failure.  
   **GREEN:** disabled commands filtered before ranking, `3` passing.

## Validation Evidence
- `npm test`: `3` passed, `0` failed.
- `node --test --experimental-test-coverage src/command-palette.test.mjs`: `100%` lines, branches, and functions.
- `git diff --check e178107..HEAD`: passed, working tree clean.
- Checkpoint commits: `cb1efd8` RED, `445752a` GREEN, `2748e85` RED, `dbc2da6` GREEN.
