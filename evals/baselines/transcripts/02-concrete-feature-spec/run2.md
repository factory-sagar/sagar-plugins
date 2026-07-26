# Scope

**Desired end state:** Every API-key-authenticated `/api/v1` request is subject to independent per-key minute and daily budgets, while health checks bypass rate limiting.

**Explicit non-goals:** IP-based limits, plan-specific quotas, a quota dashboard, and changes to authentication unrelated to identifying the API key.

**Hard constraints:** Defaults are **60 requests per minute** and **10,000 requests per day**. Reuse existing rate-limit storage if present. Health checks are exempt.

## Spec

**Goal:** Enforce atomic, per-API-key rate limits across all `/api/v1` routes without exposing API-key secrets or changing health-check behavior.

**Acceptance criteria:**
- Every non-health `/api/v1` request that successfully resolves an API key evaluates both limits before its handler runs.
- A key may receive at most 60 admitted requests in each 60-second limit window and 10,000 admitted requests in each daily limit window; distinct keys have independent budgets.
- The 61st request within an active minute window and the 10,001st request within an active daily window receive HTTP `429`, using the repository’s established API-error projection and a correct `Retry-After` header for the limiting window.
- The limiter evaluates and increments both budgets atomically, so concurrent requests cannot exceed either configured quota or leave one quota charged after rejection.
- Defaults take effect when no override is configured: `60/minute` and `10,000/day`. Configuration is parsed once at the composition boundary.
- Every `/api/v1` health-check route bypasses limiter reads and writes, while preserving its current authentication and response behavior.
- Limiter state uses existing rate-limit storage when the target repository provides it. API-key secrets are never stored, logged, traced, or included in errors; use a stable non-secret key identifier or safe fingerprint.
- Tests use a controllable clock and real seams, not module mocks or spies, to prove minute exhaustion, daily exhaustion, window reset, concurrent requests, independent keys, health exemption, error projection, and secret-safe diagnostics.
- The repository’s affected tests, type checks, lint, build checks, and review gate pass.

**Out of scope:**
- Per-IP, per-user, or anonymous-client rate limiting, because the requested policy is per API key.
- Plan-specific or customer-specific limit overrides, because only global defaults were requested.
- A client-facing quota dashboard or usage-reporting API, because enforcement is the requested outcome.
- Changing unrelated API authentication or route behavior.

**Constraints:**
- Reuse an existing rate-limit storage implementation if repository inspection finds one.
- Preserve the existing API-key authentication order and the project’s response/error conventions.
- Store and emit only non-secret API-key identifiers, never raw API-key material.
- Keep rate-limit policy in a cohesive module with explicit storage, clock, and configuration seams.
- Treat storage unavailability as a typed, safe failure and translate it at the HTTP boundary according to existing repository conventions.

**System anchor:**
- The supplied repository root contains only `.git`; no `README`, source directories, manifests, API routes, storage clients, tests, or environment configuration were found.
- `.git/config:1-5` has no remote configuration, and the repository has no commits.
- Therefore, no existing API-key resolver, `/api/v1` entrypoint, health-check inventory, storage implementation, or validation command can be cited yet.
- Source: inline repository inspection. No droid or substitute skill was used.

**Open questions:**
- Which repository or revision contains the API implementation intended by “this repo”?
- Which exact `/api/v1` paths are health checks and must be exempt?
- Does the intended runtime already have shared rate-limit storage with an atomic multi-counter operation? If not, which production storage is approved?
- Should the daily quota use a rolling 24-hour window or a calendar-day window? Recommendation: use the semantics supported atomically by the existing rate-limit store and document the reset behavior.
- Should rate-limit-store failures fail closed (`503`) or fail open? Recommendation: fail closed for authenticated API routes, preserving health-check availability.

## Decomposition

| # | Unit | Done condition | Delegate to | Reason |
|---|---|---|---|---|
| 1 | Establish the target API system anchor | Route inventory, API-key identity source, health paths, storage client, test harness, and validation commands are recorded with file references | `<self>` | The supplied repository has no implementation, and the task requires inline work without droid delegation |
| 2 | Define typed rate-limit policy and configuration | Parsed policy exposes defaults of 60/minute and 10,000/day; focused tests control time and verify policy decisions | `worker` with `tdd-workflow` | A small, independently testable functional-core unit |
| 3 | Implement the existing-store rate-limit adapter | The adapter atomically evaluates and charges both quotas using a safe API-key identifier, with typed storage-failure behavior | `worker` with `tdd-workflow` | Storage integration is the primary concurrency and correctness seam |
| 4 | Add the `/api/v1` enforcement boundary and health bypass | All protected routes receive the guard after API-key resolution, health routes bypass it, and rejections project as `429` with `Retry-After` | `worker` | Framework-specific integration should remain at the HTTP adapter boundary |
| 5 | Add integration behavior coverage | Route-level tests prove exhaustion, reset, concurrency, independent keys, health exemption, response contract, and no raw-key exposure | `test-engineer` | This is high-value behavior coverage through real seams |
| 6 | Run the repository quality gates | Relevant tests, type check, lint, and build commands pass | `<self>` with `verification-loop` | Mechanical validation after the source repository is available |
| 7 | Review the completed diff | Correctness and security review findings are resolved | `review-pr` | Rate limiting is auth-adjacent and concurrency-sensitive |
| 8 | Prepare the PR description | PR body accurately states behavior, risk, and verification | `pr-describer` | Structured change summary |
| 9 | Prepare the commit message | Conventional Commit message reflects the final diff | `commit-message-writer` | Format-specific synthesis |

## Sequence

1. Unit 1, establish the missing repository anchor.
2. Unit 2, define the policy and configuration contract after confirming local conventions.
3. Unit 3, implement the atomic storage adapter, dependent on the storage decision from unit 1.
4. Unit 4, wire the adapter into the API boundary, dependent on units 2 and 3.
5. Unit 5, prove route behavior through the actual framework seam, dependent on unit 4.
6. Unit 6, run all discovered validators.
7. Units 7 through 9, review and prepare delivery artifacts after validation passes.

## Parallelization opportunities

- Units 2 and the test-case design portion of unit 5 can proceed in parallel after unit 1 establishes the project’s testing conventions.
- Units 3 and 4 must remain sequential because the HTTP guard depends on the finalized limiter contract.
- Units 6 through 9 are sequential quality and delivery gates.

## Risk

- **Highest-risk unit:** Unit 3, because concurrent dual-window accounting must be atomic and storage semantics are currently unknown.
- **Rollback plan:** Keep the limiter as an additive module and a single API-boundary integration point, then revert that integration and module together if it causes incorrect rejections.
- **Verification gate:** Run `verification-loop` after unit 5, then `review-pr` before PR shaping.

## Hand-off after spec

The immediate next action is unit 1: restore or provide the actual API repository contents, then perform the route, authentication, storage, and validation audit before implementation.

**Deviations:** No code was changed. The supplied repository is empty, so storage selection and file-level implementation details cannot yet be truthfully specified.
