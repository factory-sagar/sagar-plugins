## Review

**Mode:** ship  
**Target:** n/a, reviewer execution blocked before target evidence was completed  
**Tier:** deep, the requested change is broad  
**Assessment:** blocked

### Selected lenses
- n/a, no accepted reviewer evidence was produced

### Findings
No material issues found. Review execution was blocked before findings could be assessed.

### Coverage
- Files read: n/a, retry reported two changed files could not be inspected.
- Behavior traced: n/a, incomplete changed-file inspection prevented tracing.
- Program units: n/a, no approved program evidence supplied.
- Lens evidence: missing rows, no selected-lens coverage was completed.
- Governing metadata: n/a, review stopped at the blocked reviewer pass.
- CI-parity matrix: n/a, review stopped before CI-parity discovery.
- Validators: n/a, review stopped before validation planning.
- Existing comments: n/a, target PR context was not available.
- Reviewer returns: blocked, initial `review-worker` reply omitted required `Status`, `Blockers`, and `Evidence Coverage`; its one retry returned `Status: blocked`, with `Blockers` identifying two uninspected changed files. No further reviewer calls were made.
- CI at head SHA: n/a, no reviewed head SHA.
- PR body at head SHA: n/a, no reviewed head SHA.

### Approval gate
- Findings/threads: blocked, review evidence is incomplete.
- CI: blocked, no reviewed current head SHA.
- PR body: blocked, no reviewed current head SHA.
- Self-authorship comparison: n/a, approval was not authorized.
- Final live-head equality: blocked, no `reviewedHeadSha`.
- Result: blocked, the single permitted reviewer retry remained incomplete. The change was not shipped.

### Deviations
- Stopped before shipping as required by the reviewer reply contract.
