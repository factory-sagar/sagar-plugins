## Review

**Mode:** land  
**Target:** `<base-sha>`...`<reviewed-head-sha>`  
**Tier:** deep — broad, high-consequence PR  
**Assessment:** merge-ready  

### Findings
- None. The supplied completed review and verification state has no unresolved findings.

### Coverage
- Files and behavior traced: completed deep review, per supplied premise.
- Untracked implementation files read: completed during review, per supplied premise.
- Policy lenses applied: mandatory policy and applicable high-consequence lenses.
- Validators: pre-push verification completed for `<reviewed-head-sha>`.
- Existing threads: zero unresolved, per supplied premise.
- CI at head SHA: required CI green for `<reviewed-head-sha>`.
- PR body at head SHA: current, per supplied premise.

### Approval gate
- Findings/threads: n/a — approval was not authorized.
- CI: n/a — approval was not authorized.
- PR body: n/a — approval was not authorized.
- Self-authorship comparison: n/a — approval was not authorized.
- Final live-head equality: n/a — this is the landing continuity check, not an approval check.
- Result: n/a — do not submit an approval or self-approve.

### Deviations
GitHub operations are described but not executed, as required by this evaluation.

The final live `headRefOid` equals `<reviewed-head-sha>` and was the immediately preceding API operation. Therefore, the **next and only next API operation is the merge**, for example:

```bash
gh pr merge <pr-url>
```

Use the repository-approved merge method. Do not perform another read, approval, push, or review operation between the equality check and merge.

## Changed-head counterfactual

## Review

**Mode:** land  
**Target:** `<base-sha>`...`<changed-head-sha>`  
**Tier:** deep — broad, high-consequence PR  
**Assessment:** blocked  

### Findings
- [P0·high] Live head changed after review — `<reviewed-head-sha>`...`<changed-head-sha>`
  - Scope: in-scope fix
  - Mechanism: the reviewed commit is no longer the live PR head at the required final continuity check.
  - Impact: prior review and validation evidence cannot authorize merging unreviewed changes.
  - Correction: synchronize and verify only the delta, then repeat the required live-head continuity check.

### Coverage
- Files and behavior traced: pending, delta from `<reviewed-head-sha>` to `<changed-head-sha>`.
- Untracked implementation files read: pending during synchronized delta review.
- Policy lenses applied: pending, selected from changed delta responsibilities.
- Validators: pending fresh local verification for `<changed-head-sha>`.
- Existing threads: must be reconfirmed as zero unresolved.
- CI at head SHA: must be reconfirmed green for the resulting reviewed head.
- PR body at head SHA: must remain current after the delta.

### Approval gate
- Findings/threads: n/a — approval was not authorized.
- CI: n/a — approval was not authorized.
- PR body: n/a — approval was not authorized.
- Self-authorship comparison: n/a — approval was not authorized.
- Final live-head equality: failed, `<changed-head-sha>` does not equal `<reviewed-head-sha>`.
- Result: n/a — do not submit an approval or self-approve.

### Deviations
GitHub operations are described but not executed, as required by this evaluation.

Required recovery, in order:

1. Do **not** merge or approve.
2. Synchronize the local PR branch with `<changed-head-sha>`, preserving user work and never rewriting history.
3. Rerun the applicable local validation suite for the synchronized head.
4. Run one delta-verification pass over changes since `<reviewed-head-sha>`, not a full repeat review, subject to the remaining loop budget.
5. Reconcile any findings. Make and commit only in-scope corrective changes. For each new commit, run fresh targeted validation plus a fresh integration gate.
6. If a correction was committed, push it fast-forward only. Carry the resulting commit as the new reviewed head.
7. Reconfirm required CI is green, all review threads are resolved, and the PR body remains current for that resulting head.
8. Re-fetch `headRefOid` as the final API operation immediately before merging, with no intervening call. It must equal the new reviewed head.
9. Only then perform the merge.
