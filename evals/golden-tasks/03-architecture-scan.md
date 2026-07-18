# Golden Task 03: Architecture Scan

## Target

`architecture-scan`.

## Prompt

```text
Look through this repo and tell me where the architecture most needs simplification. Do not change code yet.
```

## Expected behavior

The agent should perform a planning-only scan, load relevant standards topics, inspect evidence, and return ranked refactor candidates. It should not implement or estimate speculative effort.

## Must pass

- States the scan scope and confirms it is planning-only.
- Loads or references relevant `coding-standards` topics for module boundaries, type contracts, testing, and async or parsing where applicable.
- Uses file-path evidence for each candidate.
- Ranks candidates by confidence or value.
- Includes why each candidate matters, what would improve, and what a follow-up `tech-spec` should decide.
- Recommends at most 5 candidates.

## Must not do

- Edit files or propose patches.
- Give vague advice without file evidence.
- Estimate calendar effort as if it were a project plan.
- Treat all findings as equally important.
- Turn the scan into a general code review of every style nit.

## Score

- `pass`: ranked evidence-backed candidates are returned and no implementation occurs.
- `partial`: candidates are useful but one lacks concrete file evidence.
- `fail`: the agent edits files, produces broad advice only, or skips standards-backed reasoning.
