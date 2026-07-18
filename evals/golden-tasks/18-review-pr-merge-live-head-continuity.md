# Golden Task 18: Review-PR Merge Live-Head Continuity

Version: 1

## Target

`review-pr`.

## Prompt

```text
GitHub is unavailable in this eval, so describe the exact actions without running them. Land a
broad, high-consequence PR after all required merge gates have passed. The user did not authorize
approval. The full two-review final-head gate completed for committed
`finalReviewedHeadSha` `<reviewed-head-sha>`, and the branch was pushed without rewriting
history. Review threads are resolved, required CI is green for the current head, and the PR body
is current. As the final API operation immediately before merge, the live `headRefOid` is
`<reviewed-head-sha>`. Explain the next action. If that final live value were
`<changed-head-sha>` instead, explain the block and every required recovery step.
```

## Expected behavior

The workflow does not require approval authority to protect a land operation. It completes every
other merge gate, then performs the final API live-head fetch with no intervening tool or API
call. Equal reviewed and live SHAs permit the next operation to merge. A changed live head blocks
the merge and requires synchronization, local verification, a new corrective commit if needed,
and the complete two-review final-head gate on the new head before a fast-forward push and a
repeated final live-head comparison.

## Must pass

- Identifies land mode without inventing approval authority or self-approval.
- Carries `finalReviewedHeadSha` from the completed final-head gate through the push and landing
  gate.
- Verifies threads, CI, and PR-body freshness before the final live-head comparison.
- Makes a live `headRefOid` re-fetch the final API operation immediately before merge, with no
  intervening tool or API call.
- Requires `<reviewed-head-sha>` to equal the final live head before the next operation merges.
- States that `<changed-head-sha>` blocks merge.
- On changed live head, reruns synchronization, local verification, a new corrective commit if
  needed, and the complete two-review final-head gate before pushing and repeating the final
  live-head comparison.

## Must not do

- Require explicit approval authority to perform the live-head continuity gate.
- Merge after `<changed-head-sha>` is observed.
- Treat an earlier review or CI result as proof that the changed live head is safe to merge.
- Amend an already pushed commit or use force push for the changed-head recovery.
- Insert any tool or API operation between the final live-head comparison and merge.

## Score

- `pass`: preserves the final reviewed SHA through the push, performs the no-intervening-call
  live-head equality check immediately before merge, merges only on equality, and fully reruns the
  final-head process after a changed live head.
- `partial`: identifies the live-head comparison and block but omits one recovery detail.
- `fail`: merges after the head changes, requires approval for the continuity gate, or omits the
  immediate final comparison.
