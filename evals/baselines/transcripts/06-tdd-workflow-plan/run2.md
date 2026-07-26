# Completed

Implemented command-palette search suggestions.

## Behavior statement

Given available commands and a search query, when suggestions are requested, then enabled prefix-title matches appear before enabled substring-title matches, with original command order retained within each group.

## Standards loaded

- `tdd-workflow/SKILL.md`
- `coding-standards/SKILL.md`
- `TESTING_AND_VERIFICATION.md`
- `DESIGNING_MODULES.md`
- `TYPE_CONTRACTS.md`

## TDD slice

- **RED:** Added observable tests for ranking, disabled-command exclusion, and stable equal-score ordering.  
  `node --test src/command-palette.test.mjs` failed with `4` failures against `Error: not implemented`.
- **GREEN:** Implemented `suggestCommands` using ordered prefix and substring buckets, excluding `disabled` commands.  
  The focused test command then passed: `4` passed, `0` failed.

Separate commits preserve the boundary:

1. `8b49452 test(command-palette): define suggestion behavior`
2. `3b71216 feat(command-palette): suggest matching commands`

## Validation evidence

```text
$ npm test
tests 4
pass 4
fail 0
```

`git diff --check HEAD~2..HEAD` passed and the working tree is clean.
