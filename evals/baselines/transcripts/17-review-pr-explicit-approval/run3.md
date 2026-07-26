## Review

**Mode:** approve  
**Target:** `<base-sha>`...`<head-sha>`  
**Tier:** light — normal review was completed at the supplied reviewed head.  
**Assessment:** merge-ready  

### Findings
- None.

### Coverage
- Files and behavior traced: completed during the supplied normal review.
- Untracked implementation files read: completed during the supplied normal review.
- Policy lenses applied: completed during the supplied normal review.
- Validators: required CI is green for `<head-sha>`.
- Existing threads: zero unresolved, confirmed by the required GraphQL thread query.
- CI at head SHA: green for `<head-sha>`.
- PR body at head SHA: current and describes the PR.

### Approval gate
- Findings/threads: passed, zero unresolved findings and review threads.
- CI: passed, required checks are green for `<head-sha>`.
- PR body: passed, current for `<head-sha>`.
- Self-authorship comparison: passed, `<pr-author>` differs from `<current-user>`.
- Final live-head equality: passed, the immediate live `headRefOid` is `<head-sha>`, equal to `reviewedHeadSha`; immediately before approval, re-run `gh pr view <url> --json number,title,author,headRefName,headRefOid,baseRefName,state,body` with no intervening call and require the same equality.
- Result: would be submitted via `gh pr review <url> --approve --body "Review complete, required checks are green, and the PR is merge-ready."`, but was not executed — GitHub is unavailable.

### Deviations
GitHub operations were described but not executed, per the evaluation constraint.
