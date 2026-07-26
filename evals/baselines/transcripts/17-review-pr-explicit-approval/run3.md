# Review

**Mode:** approve  
**Target:** `<base SHA>...<head-sha>`  
**Tier:** light, supplied normal review completed at this tier.  
**Assessment:** merge-ready

### Selected lenses
- Completed during the supplied normal review, lens manifest was not provided.

### Findings
No material issues found.

### Coverage
- Files read: completed normal review, details not supplied.
- Behavior traced: completed normal review, details not supplied.
- Program units: n/a, none supplied.
- Lens evidence: complete in supplied normal review.
- Governing metadata: supplied PR metadata.
- CI-parity matrix: required CI supplied green for `<head-sha>`.
- Validators: supplied required-CI result.
- Existing comments: zero unresolved review threads supplied.
- Reviewer returns: complete supplied light-tier review.
- CI at head SHA: green for `<head-sha>`.
- PR body at head SHA: current.

### Approval gate
- Findings/threads: no unresolved findings, zero unresolved threads.
- CI: green for current head SHA.
- PR body: current for current head SHA.
- Self-authorship comparison: `<pr-author>` vs `<current-user>`, pass.
- Final live-head equality: `<head-sha>` = `<head-sha>`, pass.
- Result: would be submitted via `gh pr review --approve`, but was not executed, GitHub is unavailable.

The exact final sequence would be: re-fetch the live `headRefOid`, confirm it remains `<head-sha>`, then make this immediately following call with no intervening API request:

```bash
gh pr review <url> --approve --body "Review complete, required checks are green, and the PR is merge-ready."
```

### Counterfactual gates
- If `author.login` were `<current-user>`, approval would be **blocked** for self-authorship.
- If the immediate live `headRefOid` were `<changed-head-sha>`, approval would be **blocked** pending a fresh user review request and normal review of that exact head.

### Deviations
none
