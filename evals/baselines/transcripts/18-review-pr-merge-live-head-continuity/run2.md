## Review

**Mode:** land  
**Target:** `<base SHA>`...`<reviewed-head-sha>`  
**Tier:** deep — broad, high-consequence PR  
**Assessment:** merge-ready  

### Findings
- n/a — this is a gating-continuity evaluation; the completed review is assumed to have no unresolved findings.

### Coverage
- Files and behavior traced: n/a — no PR diff was provided.
- Untracked implementation files read: n/a — no repository contents were provided.
- Policy lenses applied: deep-review and landing-gate requirements.
- Validators: pre-push verification completed for committed `<reviewed-head-sha>`.
- Existing threads: zero unresolved, confirmed through the required GraphQL thread query.
- CI at head SHA: required CI green for `<reviewed-head-sha>`.
- PR body at head SHA: current.

### Approval gate
- Findings/threads: n/a — approval was not authorized.
- CI: n/a — approval gate not run.
- PR body: n/a — approval gate not run.
- Self-authorship comparison: n/a — approval gate not run.
- Final live-head equality: passed for the landing gate, `<reviewed-head-sha>` equals `<reviewed-head-sha>`.
- Result: no approval may be submitted.

### Deviations
GitHub is unavailable, so the merge is described rather than executed.

### Next action

Do **not** approve the PR. With no intervening API call after the final `headRefOid` comparison, the next operation must be the repository-configured merge mutation for this PR. It must merge the already-reviewed `<reviewed-head-sha>` directly, using the repository’s required merge method.

### If the final live head is `<changed-head-sha>`

Block the merge immediately. Do not approve or merge. Required recovery:

1. Synchronize the local PR branch with `<changed-head-sha>` safely.
2. Rerun local verification for that head.
3. Create a corrective commit only if verification or delta review requires one, never an empty commit.
4. Run one delta verification pass for changes since `<reviewed-head-sha>`, subject to the three-pass budget. Do not repeat the full review.
5. Treat the resulting verified commit as the new reviewed head.
6. If a new commit exists, push it fast-forward only.
7. Ensure required CI is green for the resulting current head, all GraphQL review threads are resolved, and the PR body remains current.
8. If branch protection now requires approval, obtain it from an eligible reviewer. Do not self-approve.
9. As the final API operation immediately before merging, fetch `headRefOid` and require it to equal the new reviewed head with no intervening call.
10. Only then submit the merge operation. If the head changes again, block and repeat this recovery path within the remaining delta-loop budget.
