## Review

**Mode:** land  
**Target:** `n/a...<reviewed-head-sha>`  
**Tier:** deep, the PR is broad and high-consequence.  
**Assessment:** merge-ready, based on the supplied gate evidence.

### Findings

No material issues found in the supplied gate state.

### Coverage

- Pre-push loop: completed for committed `reviewedHeadSha` `<reviewed-head-sha>`.
- Push: completed without history rewrite.
- Review threads: zero unresolved.
- CI: required checks green for `<reviewed-head-sha>`.
- PR body: current.
- Final live-head equality: `<reviewed-head-sha> = <reviewed-head-sha>`, pass.

### Approval gate

Approval is not authorized. Do not submit an approval. If branch protection requires approval that is not already present from another reviewer, landing is blocked rather than self-approving.

### Next action

The final live-head check passed and was the immediately preceding API operation, so the **next and only next operation** is to merge the PR using the repository-approved merge method, for example:

```bash
gh pr merge <PR_URL> --merge
```

Do not make any intervening API or tool call. This command is not executed because GitHub is unavailable in this eval.

### Counterfactual: live head is `<changed-head-sha>`

**Assessment:** blocked. Do not merge or approve.

Required recovery:

1. Synchronize the local PR branch with `<changed-head-sha>` without rewriting history.
2. Rerun local verification for the synchronized head.
3. Apply and commit a corrective change only if needed, never create an empty commit.
4. Run one fresh delta verification pass over `<reviewed-head-sha>...HEAD`, with the full current base-to-head diff as context. It must confirm prior findings remain closed and cover the correction's blast radius.
5. Record the clean resulting commit as the new `reviewedHeadSha`, then plain-push any new corrective commit.
6. Re-establish all landing gates for that new current head: resolved threads, green required CI, and a current PR body.
7. Re-fetch `headRefOid` as the final API operation immediately before merge, with no intervening call, and require equality with the new `reviewedHeadSha`.
8. Merge only if that equality check passes. If it changes again, repeat recovery subject to the three-pass delta-review budget. If exhausted, remain blocked until a new user instruction.

### Deviations

GitHub operations were described but not executed, as required.
