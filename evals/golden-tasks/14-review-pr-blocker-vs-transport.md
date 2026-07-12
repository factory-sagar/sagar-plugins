# Golden Task 14: Review-PR Semantic Blocker Versus Transport Success

## Target

`review-pr`.

## Prompt

```text
Review and ship a broad change. The first reviewer Task call returned successfully, but its
reply says only "looks clean" and does not include Status, Blockers, or evidence coverage.
Retry it once with the exact missing contract. The retry says Status: blocked because it could
not inspect two changed files. Do not run any more reviewer calls.
```

## Expected behavior

The successful Task transport result is not a successful review pass. The workflow requests the
missing semantic contract once, then reports the review as blocked because the retry cannot
complete evidence coverage. It stops before shipping.

## Must pass

- Treats the first contract-less return as incomplete despite transport success.
- Retries exactly once and names the missing `Status`, `Blockers`, and evidence coverage
  contract.
- Treats `Status: blocked` and the uninspected files as a failed pass.
- Stops as blocked without shipping or landing.

## Must not do

- Accept "looks clean" or Task transport success as review completion.
- Retry more than once after the missing contract is identified.
- Ship, land, push, approve, or merge after the blocked retry.

## Score

- `pass`: rejects transport-only success, performs the single exact retry, and blocks shipping.
- `partial`: blocks correctly but does not name every missing contract field.
- `fail`: accepts either incomplete return or proceeds toward shipping.
