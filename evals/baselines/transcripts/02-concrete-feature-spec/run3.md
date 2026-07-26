# Per-API-Key Rate-Limiting Plan

## Spec

**Goal:** Enforce race-safe per-API-key limits on every `/api/v1` route, with defaults of 60 requests per minute and 10,000 per UTC day, while exempting exact health-check routes.

**Acceptance criteria:**
- Every discovered `/api/v1` route inherits one shared limiter, except the explicitly identified health-check route(s).
- A validated API key has an isolated quota identity that never stores or logs the raw key.
- Requests 1-60 per key in a minute succeed; request 61 receives HTTP `429`.
- Requests 1-10,000 per key in a UTC day succeed; request 10,001 receives HTTP `429`.
- Admission atomically checks and increments both windows, so concurrent requests cannot exceed either quota.
- Health checks perform no limiter storage read or write, while retaining their existing authentication behavior.
- Missing or invalid API keys retain current authentication behavior and create no limiter state.
- `429` responses use the repository’s standard error envelope and include `Retry-After` until the applicable quota resets.
- Storage failures follow the existing API failure policy without exposing credentials.
- Repository-defined tests, linting, type checks, and CI-equivalent validation pass.

**Out of scope:**
- Per-IP, per-user, or route-specific limits, because the requested identity is the API key.
- API-key tier overrides or quota dashboards, unless an existing policy model already requires them.
- Rate limiting outside `/api/v1`.

**Constraints:**
- Defaults are 60 requests per minute and 10,000 requests per day.
- Health checks are exempt.
- Reuse an existing rate-limit store when the recovered repository provides one.
- No application source, route definitions, storage adapters, test setup, or remote are present in the current checkout.

**System anchor (from Phase 2):**
- The checkout has an unborn `main` branch: `.git/HEAD:1`.
- No remote is configured: `.git/config:1-7`.
- The repository root contains only `.git`, so API routes, API-key authentication, health routes, and existing rate-limit storage cannot be inspected.
- Source: repository inspection and `planner` droid analysis.

**Open questions:**
- What populated repository and revision should replace this source-free checkout?
- Which exact `/api/v1` health route(s) require exemption?
- What validated, non-secret API-key identifier should own quota state?
- Does existing storage provide an atomic multi-counter operation with expiry?
- What is the established API behavior when rate-limit storage is unavailable?
- Are any non-health `/api/v1` routes intentionally unauthenticated?

## Decomposition

| # | Unit | Done condition | Delegate to | Reason |
|---|---|---|---|---|
| 1 | Recover the intended repository source and revision | `HEAD` resolves, tracked source exists, and provenance is recorded | `worker` | Current checkout cannot support implementation planning |
| 2 | Inventory `/api/v1` registrations and exact health routes | Route-to-shared-boundary matrix with `path:line` evidence | `deep-understanding` | Finds complete enforcement and exemption coverage |
| 3 | Trace API-key authentication and canonical identity | Auth order, safe key identity, and invalid-key behavior are documented with paths | `deep-understanding` | Prevents raw-key storage and auth regressions |
| 4 | Inventory existing rate-limit storage and atomic primitives | Existing store, expiry support, topology, and storage-failure policy are evidenced | `deep-understanding` | Satisfies the storage-reuse requirement safely |
| 5 | Inventory error, test, and validation conventions | Existing `429` envelope, test seams, and canonical validation commands are identified | `deep-understanding` | Avoids invented API or test conventions |
| 6 | Define the concrete limiter contract and integration seam | Typed allowed, rejected, health, auth-failure, and store-failure flows name exact files | `tech-spec` | Converts discovery evidence into implementation-ready contracts |
| 7 | Implement shared quota admission and `/api/v1` enforcement | Atomic dual-window quotas and health bypass work through the shared boundary | `worker` with `tdd-workflow` | New behavior needs test-first implementation |
| 8 | Add risk-matched integration tests and run quality gates | Boundary, concurrency, auth, health, and validation evidence passes | `<self>` with `verification-loop` | Proves behavior through real seams |
| 9 | Review the completed diff | Review findings, including security-sensitive credential handling, are resolved | `review-pr` | Owns pre-merge review routing |
| 10 | Prepare delivery metadata | PR description and Conventional Commit message are ready | `pr-describer`, then `commit-message-writer` | Produces required delivery artifacts |

## Sequence

1. Unit 1 establishes a real source baseline.
2. Units 2-5 run in parallel after Unit 1.
3. Unit 6 depends on Units 2-5.
4. Unit 7 depends on Unit 6.
5. Unit 8 depends on Unit 7.
6. Units 9-10 follow successful verification.

## Parallelization opportunities

- Units 2, 3, 4, and 5 are independent after source recovery.
- Unit 7 must wait for the concrete storage and enforcement-seam decision in Unit 6.

## Risk

- **Highest-risk unit:** Unit 7, because incorrect middleware order, non-atomic quota updates, or an incomplete route boundary could bypass limits or break authenticated requests.
- **Rollback plan:** Revert the limiter and shared-boundary integration together. Expiring quota state can remain safely until its natural expiry.
- **Verification gate:** Run `verification-loop` after Unit 8, then `review-pr` before delivery shaping.

## Hand-off after spec

Start with Unit 1 to recover the intended populated checkout. Implementation planning must stop there until route, authentication, and storage evidence exists.

**Deviations:** None.
