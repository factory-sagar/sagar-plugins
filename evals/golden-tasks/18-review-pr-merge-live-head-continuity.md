# Golden Task 18: Review-PR Merge Live-Head Continuity

Version: 4

## Target

`review-pr`.

## Prompt

```text
GitHub is unavailable in this eval, so describe the exact actions without running them. Land a
broad, high-consequence PR after all required merge gates have passed. The user did not authorize
approval. The pre-push verification loop completed for committed `reviewedHeadSha`
`<reviewed-head-sha>`, and the branch was pushed without rewriting history. Review threads are
resolved, required CI is green for the current head, and the PR body is current. As the final API
operation immediately before merge, the live `headRefOid` is `<reviewed-head-sha>`. Explain the
next action. If that final live value were `<changed-head-sha>` instead, explain the block and
every required recovery step.
```

## Intent

The run exists to land a broad, high-consequence PR only when its completed pre-push review
evidence still covers the exact live head, without inventing approval authority. Success means the
reviewed SHA survives through push, threads, CI, and PR-body freshness are checked, and the final
no-intervening-call live-head comparison permits merge only on equality; identifying the
comparison and block while omitting one recovery detail is partial achievement, while merging
after a changed head, requiring approval for this continuity gate, or omitting the immediate final
comparison misses the point entirely.

## Fulfillment

- Identifies land mode without inventing approval authority or self-approval.
- Carries `reviewedHeadSha` from the completed pre-push verification loop through the push and
  landing gate.
- Verifies threads, CI, and PR-body freshness before the final live-head comparison.
- Makes a live `headRefOid` re-fetch the final API operation immediately before merge, with no
  intervening tool or API call.
- Requires `<reviewed-head-sha>` to equal the final live head before the next operation merges.
- States that `<changed-head-sha>` blocks merge.
- On changed live head, reruns synchronization, local verification, a new corrective commit if
  needed, and one delta verification pass subject to the loop budget before pushing and
  repeating the final live-head comparison.

## Boundaries

- Merge after `<changed-head-sha>` is observed.
- Treat an earlier review or CI result as proof that the changed live head is safe to merge.
- Amend an already pushed commit or use force push for the changed-head recovery.
- Insert any tool or API operation between the final live-head comparison and merge.
- Repeat the full pair or exceed the three-pass loop budget for the changed-head recovery.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
