## Review

**Mode:** report  
**Target:** `bf82a20...ef6cbbf`  
**Tier:** deep, the new worker processes externally controlled webhook state, mutates coupled cache and SQL state, retries failures, and changes authorization-relevant roles.  
**Assessment:** needs changes

### Selected lenses
- `mandatory` - mandatory for every changed behavior
- `secrets-privacy-observability` - logging and bearer-token handling were added

### Findings
- [P1·high] Authenticate and authorize webhook role changes before mutation - `process_job.py:9-19`
  - Mechanism: Untrusted JSON supplies `tenant_id`, `user_id`, and `role` directly. The worker neither verifies the bearer token nor checks that its principal may assign the requested role before updating both the cache and `tenant_roles`.
  - Impact: Anyone able to submit a job can grant arbitrary tenant roles, including administrator access.
  - Correction: Verify the webhook signature or bearer token at the boundary, derive the actor and tenant from verified credentials, and authorize the requested role transition before any state change.

- [P1·high] Do not log bearer tokens - `process_job.py:25`
  - Mechanism: `logger.info` renders the raw `bearer_token`; the exercised path confirmed the token reaches the final log message.
  - Impact: Logs become reusable credentials for any reader, exporter, or incident system receiving them.
  - Correction: Remove the token from logs and retain only non-secret job metadata if observability is needed.

- [P1·high] Commit SQL and cache membership atomically - `process_job.py:15-23`
  - Mechanism: The cache is updated before the SQL write. On database failure, the retry is enqueued but the in-memory cache remains set to the uncommitted role. The failure-path harness reproduced this divergence.
  - Impact: Authorization checks using the cache can grant a role the database rejected, and retries can act on inconsistent state.
  - Correction: Update or invalidate the cache only after a successful durable write, or use a transaction/compensation strategy that restores both stores together.

- [P2·high] Add real-seam coverage for the worker contract - `process_job.py:8-25`
  - Mechanism: No tests or test configuration exist, despite new parsing, persistence, retry, cache, authorization, and secret-handling behavior.
  - Impact: The security and consistency regressions above are unguarded.
  - Correction: Add interface-level tests covering rejected/unverified payloads, allowed role transitions, SQL failure without cache mutation, retry behavior, and log redaction.

### Coverage
- **Files read:** `worker/process_job.py`, its base version, governing review contract and selected policy sections.
- **Behavior traced:** webhook parse to cache and SQL mutation, SQL failure to retry, success telemetry.
- **Program units:** no approved program or linked issue present.
- **Lens evidence:** complete.
- **Governing metadata:** no README, `AGENTS.md`, manifest, workflows, remote, or test configuration exists in the target repository.
- **CI-parity matrix:** n/a, no CI workflow exists.
- **Validators:** Python syntax compilation passed; `git diff --check` passed.
- **Existing comments:** n/a, this is a local range rather than a PR.
- **Reviewer returns:** inline review required by request, no droid substituted.
- **CI at head SHA:** n/a, no CI configured.
- **PR body at head SHA:** n/a.

### Deviations
Inline review was performed as requested, rather than delegating to a reviewer droid.
