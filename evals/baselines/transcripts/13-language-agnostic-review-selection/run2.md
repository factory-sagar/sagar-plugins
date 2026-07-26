## Review

**Mode:** report  
**Target:** `f72705237462d4ce95457801ccb7176f470a8e15...daadde8d66ec37c1a9459801334bd301ff3bf14d`  
**Tier:** deep — externally controlled tenant-role mutation, shared cache, persistence, retry workflow, and credential handling  
**Assessment:** needs changes  

**Selected review lenses:** intent and completeness; correctness and invariants; tests and evidence; failures; ownership and mutation; boundaries and contracts; mutation and state ownership; authentication and authorization; external input and injection; persistence; async, concurrency, and distributed work; secrets, privacy, and observability; operations and rollback.

### Findings
- [P0·high] Unverified webhook claims can assign arbitrary tenant roles — `process_job.py:9`
  - Scope: scope-expanding proposal
  - Mechanism: Payload-provided tenant, user, and role are used as authoritative values, while the bearer token is never authenticated or authorized.
  - Impact: A forged webhook can grant privileged roles across tenants.
  - Correction: Define and implement the webhook authentication and authorization contract, derive tenant scope from verified identity, and allowlist valid roles before mutation.

- [P0·high] Bearer token is logged in plaintext — `process_job.py:25`
  - Scope: in-scope fix
  - Mechanism: The success log interpolates `bearer_token` directly.
  - Impact: Log readers and downstream log systems can recover a reusable credential.
  - Correction: Remove the token from logs and use only explicitly safe correlation data.

- [P1·high] Cache state is published before persistence succeeds — `process_job.py:15`
  - Scope: in-scope fix
  - Mechanism: The cache is updated before SQL executes and is not reverted on failure. A zero-row `UPDATE` is also accepted as success.
  - Impact: Authorization consumers can observe a role absent from durable storage.
  - Correction: Verify a successful durable update affecting the expected membership before updating the cache, preserving prior cache state on failure.

- [P1·high] All database failures are retried indiscriminately — `process_job.py:21`
  - Scope: in-scope fix
  - Mechanism: `except Exception` retries transient and permanent failures identically.
  - Impact: Poison jobs can loop indefinitely and exhaust worker or database capacity.
  - Correction: Retry only classified transient failures and send permanent rejections through the terminal failure path.

- [P1·high] Raw identifiers and roles bypass boundary validation — `process_job.py:9`
  - Scope: in-scope fix
  - Mechanism: Parsed JSON is assumed to have valid, hashable identifiers and an allowed role before any side effect.
  - Impact: Malformed messages can crash the worker or persist invalid authorization state.
  - Correction: Validate payload shape, identifier types, required fields, and allowed role values before mutation.

- [P2·high] No regression coverage protects the worker’s critical paths — `process_job.py:8`
  - Scope: in-scope fix
  - Mechanism: No tests cover success, failed or zero-row persistence, retry classification, cache consistency, input rejection, or token-safe logging.
  - Impact: The defects above can regress undetected.
  - Correction: Add entrypoint-level tests covering these outcomes.

### Coverage
- Files and behavior traced: `process_job.py:1-25`, including JSON parsing, cache mutation, SQL update, retry, and logging.
- Untracked implementation files read: none, worktree was clean.
- Policy lenses applied: selected lenses listed above. Parameterized SQL was verified safe from direct SQL injection.
- Validators: `python3` AST syntax parse passed; `git diff --check main...HEAD` passed. No repository test, lint, typecheck, or build configuration exists.
- Existing threads: n/a, local branch-range review.
- CI at head SHA: n/a, no PR target.
- PR body at head SHA: n/a, no PR target.

### Approval gate
- Findings/threads: n/a — report mode, findings remain.
- CI: n/a — no PR target.
- PR body: n/a — no PR target.
- Self-authorship comparison: n/a — report mode.
- Final live-head equality: n/a — report mode.
- Result: n/a — approval was not authorized.

### Deviations
Added the selected-lenses line before findings to honor the requested review ordering.
