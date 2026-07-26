## Review

**Mode:** report  
**Target:** `536f830afda04d7a5cec6bf84913216123cecc7a...32b6a41a314fc1c944f6d660b4ddc482b83d4363`  
**Tier:** deep, webhook-controlled role changes coordinate shared state, SQL persistence, retries, and credentials.  
**Assessment:** needs changes

### Selected lenses
- **Mandatory**: applies to every changed behavior.
- **Secrets, Privacy, and Observability**: the new logger records a bearer token.

### Findings
- [P1·high] Do not log or requeue bearer credentials, `worker/process_job.py:13,22-25`
  - Mechanism: logs the raw bearer token and sends the raw webhook, including that token, to retry infrastructure.
  - Impact: reusable credentials can leak through logs and possibly persistent queues.
  - Correction: omit the token from telemetry and retry only a minimal, secret-free command.

- [P1·medium] Authenticate and authorize role mutations, `worker/process_job.py:10-20`
  - Mechanism: tenant, user, and role are accepted from the webhook without visible verification or role allowlisting.
  - Impact: a forgeable or replayed job could grant arbitrary tenant roles.
  - Correction: verify trusted webhook identity and authorize the role transition before mutation. Upstream authentication is not present in this repository, so this finding is confidence-qualified.

- [P1·high] Publish cache state only after a confirmed durable update, `worker/process_job.py:15-25`
  - Mechanism: cache mutation precedes SQL execution; zero-row updates are accepted; no transaction-ownership contract is established.
  - Impact: cache can authorize a role that SQL did not persist.
  - Correction: require a committed, affected-row-confirmed transition before cache publication and success logging.

- [P1·high] Make delivery ordering and replay handling durable, `worker/process_job.py:9-24`
  - Mechanism: no event identity, ordering version, per-key serialization, or persisted retry progress exists.
  - Impact: stale, concurrent, or redelivered jobs can reverse roles or leave cache and SQL divergent.
  - Correction: use a durable idempotency identity and guarded/versioned tenant-role transition.

- [P1·medium] Classify retryable failures and preserve the original error, `worker/process_job.py:21-23`
  - Mechanism: `except Exception` retries permanent failures, and a retry-callback error replaces the database failure.
  - Impact: futile retries, duplicate delivery, and lost diagnostic cause.
  - Correction: classify transient database failures, assign retry ownership once, and preserve the initiating exception.

- [P2·high] Validate webhook shape before mutation, `worker/process_job.py:9-15`
  - Mechanism: JSON decoding and key extraction do not establish object shape, field types, allowed roles, or terminal-input handling.
  - Impact: malformed or semantically invalid input has incidental failure behavior and can reach cache logic.
  - Correction: parse a strict membership command at the boundary and explicitly dead-letter invalid input.

- [P2·high] Add regression coverage and a canonical validation gate, `worker/process_job.py:8-25`
  - Mechanism: the repository has no tests, manifest, or CI workflow.
  - Impact: cache/SQL consistency, retry semantics, role validation, and token-redaction regressions have no executable protection.
  - Correction: add caller-facing tests, including representative database behavior, and wire them into CI.

- [P3·high] Use a domain-specific handler name, `worker/process_job.py:8`
  - Mechanism: `process_job` obscures the membership-role action.
  - Impact: callers cannot identify the operation from its interface.
  - Correction: rename it to a concrete domain action, such as `apply_tenant_membership`.

### Coverage
- **Files read:** `worker/process_job.py`
- **Behavior traced:** webhook parsing, cache mutation, SQL update, zero-row result, failure/retry flow, replay/concurrency, and token logging.
- **Program units:** no approved program or PR metadata available.
- **Lens evidence:** complete.
- **Governing metadata:** no README, AGENTS.md, manifest, tests, docs, or workflows exist.
- **CI-parity matrix:** n/a, no configured CI or local project gate.
- **Validators:** `git diff --check` and Python syntax compilation passed.
- **Existing comments:** n/a, range review rather than PR.
- **Reviewer returns:** complete, including independent challenge and security passes.
- **CI at head SHA:** n/a.
- **PR body at head SHA:** n/a.

### Approval gate
- **Result:** n/a, approval was not authorized.

### Deviations
None. The repository remains clean and unchanged.
