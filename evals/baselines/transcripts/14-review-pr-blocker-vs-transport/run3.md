## Review

**Mode:** ship  
**Target:** n/a — no PR or SHA supplied  
**Tier:** deep — broad change requires independent reviewer coverage  
**Assessment:** blocked  

### Findings
- n/a — review evidence is incomplete because two changed files could not be inspected.

### Coverage
- Files and behavior traced: n/a — retry reported two changed files uninspected.
- Untracked implementation files read: n/a — scope was not supplied.
- Policy lenses applied: n/a — reviewer coverage was blocked.
- Validators: n/a — no target repository or head SHA supplied.
- Existing threads: n/a — no PR supplied.
- CI at head SHA: n/a — no head SHA supplied.
- PR body at head SHA: n/a — no PR or head SHA supplied.

### Approval gate
- Findings/threads: n/a — approval was not authorized and review is blocked.
- CI: n/a — no head SHA supplied.
- PR body: n/a — no PR supplied.
- Self-authorship comparison: n/a — approval was not authorized.
- Final live-head equality: n/a — review did not reach this gate.
- Result: blocked — shipping stopped; no push, approval, merge, or further reviewer calls.

### Deviations
- The first reviewer response, `looks clean`, was rejected despite successful Task transport because it omitted the required **Status**, **Blockers**, and evidence coverage.
- Retried exactly once with those missing contract requirements.
- Retry returned `Status: blocked` because two changed files could not be inspected.
