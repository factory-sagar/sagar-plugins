# Golden Task 06: TDD Workflow Plan

## Target

`tdd-workflow`.

## Prompt

```text
Use TDD to add search suggestions to the command palette. Suggestions should rank prefix matches above substring matches, hide disabled commands, and preserve the original command order for equal scores.
```

## Expected behavior

The agent should plan vertical Red-Green-Refactor slices around observable behavior. It should load testing and relevant standards topics, then delegate RED and GREEN work appropriately.

## Must pass

- Starts from a user-facing or contract-facing behavior statement.
- Loads or references testing, module-design, type-contract, and async standards where relevant.
- Plans RED tests before implementation.
- Uses vertical slices, not "write all tests, then all code."
- Includes tests for prefix-vs-substring ranking, disabled command hiding, and stable ordering for equal scores.
- Delegates RED to `test-engineer` or `worker` with a test-only prompt.
- Delegates GREEN to `implementer` or `worker` with a minimal-implementation prompt.
- Requires verification after the loop.

## Must not do

- Implement before writing failing tests.
- Modify tests during GREEN unless the RED tests are invalid.
- Use implementation-detail assertions instead of observable command-palette results.
- Treat coverage percentage as a substitute for behavior coverage.

## Score

- `pass`: the plan is test-first, vertical, and standards-aware.
- `partial`: the plan is test-first but too horizontal.
- `fail`: the plan writes implementation first or omits the seeded behaviors.
