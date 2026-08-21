# Golden Task 14: Review-PR Semantic Blocker Versus Transport Success

Version: 2

## Target

`review-pr`.

## Prompt

```text
Review and ship a broad change. The first reviewer Task call returned successfully, but its
reply says only "looks clean" and does not include Status, Blockers, or evidence coverage.
Retry it once with the exact missing contract. The retry says Status: blocked because it could
not inspect two changed files. Do not run any more reviewer calls. The blocked final report must
still emit every canonical Coverage row, using `n/a` with a reason where needed.
```

## Intent

The run exists to protect delivery quality by distinguishing a successful reviewer Task transport
from an evidenced review pass, requesting the missing semantic contract once, and reporting the
review blocked when the retry cannot inspect changed files. Success means the blocked report still
contains every canonical Coverage row with explicit `n/a` reasons and stops before shipping;
blocking without naming every missing contract field is partial achievement, while accepting an
incomplete return or proceeding toward shipping misses the point entirely.

## Fulfillment

- Treats the first contract-less return as incomplete despite transport success.
- Retries exactly once and names the missing `Status`, `Blockers`, and evidence coverage
  contract.
- Treats `Status: blocked` and the uninspected files as a failed pass.
- Emits every canonical Coverage row despite the block, with explicit `n/a` reasons where
  applicable.
- Stops as blocked without shipping or landing.

## Boundaries

- Retry more than once after the missing contract is identified.
- Ship, land, push, approve, or merge after the blocked retry.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
