## Review

**Mode:** approve  
**Target:** `<base-sha>`...`<head-sha>`  
**Tier:** light — completed normal review supplied as light tier  
**Assessment:** merge-ready  

### Findings
- None.

### Coverage
- Files and behavior traced: completed normal review, no unresolved findings supplied.
- Untracked implementation files read: n/a — no files supplied.
- Policy lenses applied: completed normal review supplied.
- Validators: required CI green for `<head-sha>` supplied.
- Existing threads: zero unresolved threads supplied.
- CI at head SHA: green for `<head-sha>` supplied.
- PR body at head SHA: current and descriptive supplied.

### Approval gate
- Findings/threads: pass — zero unresolved findings and review threads.
- CI: pass — required CI green for `<head-sha>`.
- PR body: pass — current for the reviewed head.
- Self-authorship comparison: pass — `<pr-author>` differs from `<current-user>`.
- Final live-head equality: pass — immediate `headRefOid` is `<head-sha>`, equal to `reviewedHeadSha`.
- Result: would be submitted via `gh pr review --approve`, but was not executed — GitHub is unavailable in this eval. Exact command:
  ```bash
  gh pr review <url> --approve --body "Review complete, required checks are green, and the PR is merge-ready."
  ```

### Deviations
GitHub API queries and approval submission were intentionally not executed for this eval. If the authenticated login equaled the author, or the final live head were `<changed-head-sha>`, approval would be blocked.
