## Review

**Mode:** report  
**Target:** `62f51d4c3bbaaa6023884d9624cda67a37f27358...77c51e6978d348d70598644435640a6fa597b6ba`  
**Tier:** deep, the new worker handles externally supplied authorization state, shared mutable state, persistence, retries, and credentials.  
**Assessment:** needs changes

### Selected lenses
- `mandatory` — mandatory for every changed behavior
- `secrets-privacy-observability` — new logger emits the bearer token

### Findings
- [P0·high] Bearer credential is logged verbatim — `worker/process_job.py:25`
  - Mechanism: The success log interpolates `bearer_token`, exposing a replayable credential to log readers and sinks.
  - Impact: Credential theft and user impersonation.
  - Correction: Do not log the token. Use only approved, non-secret correlation data.

- [P1·high] Failed persistence leaves the membership cache inconsistent — `worker/process_job.py:15-23`
  - Mechanism: The cache updates before `connection.execute`; an exception retries and re-raises without restoring or invalidating the cache.
  - Impact: Consumers can observe a role that was never stored, including an unintended elevated role.
  - Correction: Persist first, then publish to the cache only after success, or restore/invalidate cache state on failure.

- [P1·high] Webhook fields are used without boundary validation — `worker/process_job.py:9-19`
  - Mechanism: Decoded JSON is indexed and its tenant, user, and role values mutate cache and SQL state without shape, type, or role validation.
  - Impact: Malformed events raise unclassified exceptions and invalid values can reach authorization state.
  - Correction: Parse into a validated membership event before any state mutation, rejecting malformed and invalid input.

- [P1·medium] Every persistence exception is retried — `worker/process_job.py:21-23`
  - Mechanism: `except Exception` schedules retry for transient, permanent, and programming failures alike.
  - Impact: Permanent poison jobs can loop indefinitely.
  - Correction: Retry only classified transient failures and route terminal failures separately.

- [P2·high] No regression coverage protects this stateful worker — `worker/process_job.py:8-25`
  - Mechanism: The repository has no tests for parsing, cache/database consistency, retries, or secret-safe logging.
  - Impact: The listed failures can regress undetected.
  - Correction: Add public-seam tests for valid input, malformed input, persistence failure, retry classification, cache consistency, and log redaction.

### Coverage
- **Files read:** `worker/process_job.py`, full `main...HEAD` diff, repository metadata inventory.
- **Behavior traced:** parsing, cache update, bound SQL update, retry/rethrow, success logging.
- **Program units:** no approved program supplied.
- **Lens evidence:** complete. SQL parameter binding and tenant/user predicates were verified clean.
- **Governing metadata:** no README, AGENTS.md, manifest, tests, or CI workflow exists.
- **CI-parity matrix:** n/a, no CI jobs or project validation commands are defined.
- **Validators:** `compile(...)`, in-memory behavior probe, and `git diff --check` passed.
- **Existing comments:** n/a, branch-range review.
- **Reviewer returns:** complete, including `change-review`, security, deep primary/fallback, and independent challenge review.
- **CI at head SHA:** n/a, no remote or CI configuration.
- **PR body at head SHA:** n/a, not a PR.

### Approval gate
n/a, report mode.

### Deviations
The resumed deep-review worker produced no new evidence, so the required comprehensive fallback was used. The independent challenge worker was retried once after its initial response lacked a designated separate notes path.
