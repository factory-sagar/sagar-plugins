## Review

**Mode:** ship  
**Target:** `n/a` (checkout has no commits, refs, or diff)  
**Tier:** deep, requested as a broad change  
**Assessment:** blocked

### Selected lenses
- mandatory, mandatory for every changed behavior

### Findings
- Not assessed, the review-worker pass remained blocked before file inspection.

### Coverage
- Files read: `n/a`, changed-file identities unavailable.
- Behavior traced: `n/a`, neither changed file could be inspected.
- Program units: `n/a`, no approved program or diff was available.
- Lens evidence: missing, mandatory lens cannot be evidenced without the two files.
- Governing metadata: `n/a`, no changed directories exist in the checkout.
- CI-parity matrix: `n/a`, no project or workflow exists in the checkout.
- Validators: `n/a`, no reviewable implementation target exists.
- Existing comments: `n/a`, no PR target was supplied.
- Reviewer returns: blocked, initial transport-success return omitted `Status`, `Blockers`, and `Evidence Coverage`; its one permitted retry returned `Status: blocked` because two changed files could not be inspected, with incomplete evidence coverage.
- CI at head SHA: `n/a`, no head SHA exists.
- PR body at head SHA: `n/a`, no PR exists.

### Approval gate
- Findings/threads: blocked, review is incomplete; threads are `n/a` without a PR.
- CI: `n/a`, no current head SHA.
- PR body: `n/a`, no PR exists.
- Self-authorship comparison: `n/a`, no PR author or authenticated target.
- Final live-head equality: `n/a`, no reviewed or live head SHA.
- Result: blocked, shipping is prohibited after the permitted reviewer retry remained blocked.

### Deviations
No additional reviewer calls were made after the single permitted retry.
