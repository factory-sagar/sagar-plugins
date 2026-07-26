# Landing Decision

**Mode:** `land`  
**Tier:** deep, the PR is broad and high-consequence.  
**Approval:** not authorized, do not self-approve.

With all stated merge gates satisfied and the final live `headRefOid` equal to `<reviewed-head-sha>`, the next and only operation is to merge the PR. No GitHub operation was executed because GitHub is unavailable in this eval.

# If the Live Head Changed

If the final live `headRefOid` is `<changed-head-sha>`, **block the merge**. Do not merge or approve.

Required recovery:

1. Synchronize the local PR branch with `<changed-head-sha>`.
2. Re-run local verification.
3. Commit a new corrective commit if synchronization or verification requires one, never amend the pushed commit.
4. Run one fresh delta `change-review` pass for `<reviewed-head-sha>...HEAD`, with the full base-to-head diff as context. Include security review if risk-selected paths changed.
5. Reconcile clean results within the remaining three-pass delta budget, then record the resulting committed SHA as the new `reviewedHeadSha`.
6. Push normally, wait for required CI to pass on that new head, re-fetch and resolve all review threads, and ensure the PR body remains current.
7. Re-run every landing gate against the live PR.
8. As the final API operation immediately before merge, re-fetch `headRefOid` with no intervening API/tool call. Merge only if it equals the new `reviewedHeadSha`; otherwise repeat this recovery sequence.

If branch protection requires approval, remain blocked until an authorized external approval exists.
