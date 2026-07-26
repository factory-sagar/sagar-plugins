## Review

**Mode:** land  
**Target:** `<base-sha>`...`<reviewed-head-sha>`  
**Tier:** deep, broad high-consequence change  
**Assessment:** merge-ready  

### Findings
- None, all required merge gates are stated as passed.

### Coverage
- Files and behavior traced: n/a (contract scenario, no diff supplied)
- Untracked implementation files read: n/a (contract scenario)
- Policy lenses applied: deep-review and landing gate
- Validators: pre-push verification completed for `<reviewed-head-sha>`
- Existing threads: zero unresolved, per premise
- CI at head SHA: green for `<reviewed-head-sha>`, per premise
- PR body at head SHA: current, per premise

### Approval gate
- Findings/threads: n/a (approval was not authorized)
- CI: n/a (approval was not authorized)
- PR body: n/a (approval was not authorized)
- Self-authorship comparison: n/a (approval was not authorized)
- Final live-head equality: `<reviewed-head-sha>` equals reviewed head
- Result: no approval action is permitted or required

### Deviations
none

## Next Action

Perform the merge operation immediately, with no intervening API call. Do not self-approve. The merge uses the repository's configured merge method.

## If the Final Live Head Were `<changed-head-sha>`

Block the merge. Then:

1. Synchronize local state with `<changed-head-sha>`.
2. Rerun local verification for that live head.
3. If necessary, make and commit an in-scope corrective commit.
4. Run one deep delta-verification pass over changes since `<reviewed-head-sha>`, subject to the review-loop budget. Do not repeat the full review.
5. Carry the resulting reviewed head through a fast-forward push, without rewriting history.
6. Refresh the PR body for the resulting head, then confirm required CI is green and all review threads are resolved.
7. As the final pre-merge API operation, re-fetch `headRefOid` and require equality with the resulting reviewed head, with no intervening call.
8. Only then perform the merge operation.
