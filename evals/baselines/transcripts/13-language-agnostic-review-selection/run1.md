## Review

**Mode:** report  
**Target:** `9482828189c03d737aed31e732e61cd2ad584ce3...8b902f14df31c69f555d98155f11f757d9ea3ab7`  
**Tier:** deep, the worker combines external input, shared cache mutation, tenant authorization data, SQL, retries, and secret-bearing telemetry.  
**Assessment:** needs changes  

### Findings

**Selected review lenses:** intent and completeness; correctness and invariants; tests and evidence; mutation and state ownership; authentication and authorization; external input and injection; async, concurrency, and distributed work; secrets, privacy, and observability; persistence; operations and rollback.

- [P1·high] Bearer token is logged in plaintext, exposing reusable credentials — `worker/process_job.py:25`
  - Scope: in-scope fix
  - Mechanism: The success log interpolates `bearer_token` directly into the message.
  - Impact: Anyone with access to worker logs can replay the credential and impersonate the webhook caller.
  - Correction: Remove the token from logs and emit only non-sensitive, bounded job identifiers.

- [P1·high] Failed database writes leave the shared membership cache claiming an uncommitted role — `worker/process_job.py:15-23`
  - Scope: in-scope fix
  - Mechanism: The cache is updated before `connection.execute`; when the SQL update raises, the worker retries but preserves the speculative cache value.
  - Impact: Readers can authorize a user using a role that was never persisted. Retried or duplicate jobs can also observe and build on inconsistent cache state.
  - Correction: Update the cache only after a successful database write, or restore its exact prior value on failure within the same ownership boundary.

- [P2·high] The new worker has no regression coverage for parsing, persistence failures, retries, cache consistency, or safe logging — `worker/process_job.py:8-25`
  - Scope: in-scope fix
  - Mechanism: The repository contains only this module and no tests or test configuration.
  - Impact: The two demonstrated failure modes can recur without detection, and malformed webhook handling remains unverified.
  - Correction: Add entrypoint-level tests that prove SQL failure does not publish a cache change, retries receive the expected payload, and logs never contain the bearer token.

### Coverage
- Files and behavior traced: `worker/process_job.py`; webhook JSON parsing, shared cache update, parameterized tenant-role SQL update, exception/retry flow, and success logging.
- Untracked implementation files read: No implementation files were untracked before review. Validation generated and inspected `worker/__pycache__/process_job.cpython-314.pyc`.
- Policy lenses applied: Intent and completeness, correctness and invariants, tests and evidence, mutation and state ownership, authentication and authorization, external input and injection, persistence, async/distributed work, secrets/privacy/observability, operations and rollback.
- Validators: `git diff --check main...HEAD` passed; `python3 -m py_compile worker/process_job.py` passed; targeted behavioral probe reproduced cache divergence and token disclosure. `python3 -m unittest discover` found zero tests and exited 5.
- Existing threads: n/a, review target is a local `main...HEAD` range rather than a PR.
- CI at head SHA: n/a, no PR or CI metadata is available.
- PR body at head SHA: n/a, no PR is associated with the requested range.

### Approval gate
- Findings/threads: Fails, three findings remain; PR threads are n/a.
- CI: n/a, approval was not authorized and no PR was supplied.
- PR body: n/a, no PR was supplied.
- Self-authorship comparison: n/a, approval was not authorized.
- Final live-head equality: n/a, approval was not authorized.
- Result: Not run, report-only mode.

### Deviations
A validation-generated untracked bytecode artifact remains at `worker/__pycache__/process_job.cpython-314.pyc`; it was not removed because untracked files are protected.
