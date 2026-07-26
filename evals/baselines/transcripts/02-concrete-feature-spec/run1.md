## Scope

Add per-API-key enforcement to every non-health `/api/v1` route. The default budgets are **60 requests per minute** and **10,000 per day**; existing rate-limit storage must be reused if the actual application repository contains it.

## Spec

**Goal:** Authenticated API keys are independently limited across all non-health `/api/v1` endpoints without exposing key material or changing existing authentication behavior.

**Acceptance criteria:**
- Every `/api/v1` route identified by the route inventory applies the rate-limit gate after successful API-key authentication, except identified health-check routes.
- An API key with no quota override receives 60 allowed requests in its active minute window and 10,000 allowed requests in its active daily window.
- The next request exceeding either budget receives HTTP `429` through the repository’s established error projection, with an integer `Retry-After` header representing when the request may be retried.
- Requests using one API key do not consume, block, or reset another key’s budget.
- The limiter uses an internal stable key identifier or one-way non-secret derivative, never the raw API key, in storage keys, errors, logs, metrics, traces, or test snapshots.
- The store operation evaluates and consumes the minute and daily budget atomically, so a rejected request cannot partially consume the other window.
- Health-check routes bypass all limiter reads and writes and do not consume quota; their pre-existing authentication and response behavior otherwise remains unchanged.
- Missing quota configuration resolves to `60` per minute and `10,000` per day. Invalid configured quotas are rejected at the application configuration boundary rather than silently disabling protection.
- Behavior tests control time and assert: under quota, minute exhaustion, day exhaustion, independent keys, rejection retry timing, and health-check exemption.
- Integration tests exercise the real API/auth seam and confirm an invalid API key remains an authentication failure without creating rate-limit state.

**Out of scope:**
- Per-IP, per-user, endpoint-specific, or tier-based quotas, these are separate policies.
- A customer-facing quota dashboard or rate-limit response headers beyond required `Retry-After`.
- Changing API-key issuance, revocation, or health-check authentication policy.
- Provisioning a new datastore before the actual application repository establishes that existing storage cannot satisfy the atomic cross-instance requirement.

**Constraints:**
- Reuse the repository’s existing rate-limit storage if present, and retain its established client, lifecycle, telemetry, and failure conventions.
- Preserve the auth-before-limit ordering for protected API routes.
- Parse rate-limit configuration once at the composition boundary into positive integer values.
- Keep limiter policy in a cohesive service module behind a narrow storage seam; framework route handlers only authenticate, invoke it, and project responses.
- Classify storage failures safely and never include raw API keys or arbitrary storage errors in observability output.

**System anchor:**
- The supplied repository root contains only `.git/`; it has no `README`, source files, API routes, authentication implementation, health routes, configuration, tests, or rate-limit storage to inspect.
- Consequently, no existing rate-limit storage can be identified and no repository-specific file:line references can yet be provided.
- Source: repository-root directory listing and the supplied `spec` contract at `plugins/practices/skills/spec/SKILL.md`.

**Open questions:**
- Which repository contains the actual application source to inventory for `/api/v1`, API-key authentication, health routes, and existing storage?
- Which stable non-secret API-key identity should index limits, preferably the persisted API-key ID rather than a raw-key hash?
- Does the existing storage provide an atomic multi-window primitive that is shared across all application instances?
- Which exact `/api/v1` health-check paths exist, and must they remain authenticated?
- On rate-limit storage failure, should the API fail closed with a safe `503` response (recommended) or fail open?
- Are deployment-configured quota overrides required beyond the stated defaults?

## Decomposition

| # | Unit | Done condition | Delegate to | Reason |
|---|---|---|---|---|
| 1 | Inventory route, auth, health, storage, config, and test seams | A file:line system map identifies all `/api/v1` entrypoints, health routes, API-key identity, existing storage, and validators | `deep-understanding` | The current repository has no application code, so evidence gathering is the blocking task |
| 2 | Define parsed quota configuration and the limiter storage contract | Defaults, invalid-config behavior, stable key identity, atomic result shape, and storage-failure contract are testable and match repository conventions | `worker` with `tdd-workflow` | Creates the narrow typed seam before framework wiring |
| 3 | Implement and test the atomic per-key quota service | Behavior tests prove independent minute/day limits, no partial consumption, retry timing, and no raw-key persistence | `worker` with `tdd-workflow` | Encapsulates rate-limit policy behind the storage seam |
| 4 | Integrate the limiter after API-key authentication for all `/api/v1` routes | Authenticated over-quota requests return `429`; invalid keys retain existing auth behavior | `worker` | Route integration is the highest-risk protocol change |
| 5 | Add health-check bypass behavior and integration coverage | Each identified health route performs no limiter operation and preserves current behavior | `test-engineer` | Verifies the explicit exemption through the API seam |
| 6 | Add safe limiter observability and storage-failure coverage | Errors and telemetry use stable safe fields only, and the chosen unavailable-store behavior is tested | `worker` | Covers security-sensitive failure translation |
| 7 | Run repository quality gates | Targeted tests, full tests, lint, type checks, and applicable build checks pass | `<self>` with `verification-loop` | Mechanical validation against repository-defined gates |
| 8 | Review the complete diff | Correctness and security review findings are resolved | `review-pr` | Auth-adjacent throttling needs risk-matched review |
| 9 | Draft the PR description | PR description covers behavior, storage choice, failure mode, and verification evidence | `pr-describer` | Produces repository-ready change summary |
| 10 | Draft the commit message | Conventional Commit message reflects the final diff | `commit-message-writer` | Format-mechanical final step |

## Sequence

1. Unit 1 establishes the missing system anchor and resolves storage feasibility.
2. Unit 2 depends on Unit 1’s storage, configuration, and API-key identity findings.
3. Unit 3 depends on Unit 2’s explicit limiter contract.
4. Unit 4 depends on Unit 3’s callable limiter service.
5. Unit 5 depends on Unit 4’s route integration and the health-route inventory from Unit 1.
6. Unit 6 depends on Units 3 and 4.
7. Unit 7 runs after Units 5 and 6.
8. Unit 8 follows a green verification gate.
9. Units 9 and 10 follow the completed review.

## Parallelization opportunities

- After Unit 1, Units 2’s configuration contract and Unit 5’s health-route test cases can be prepared in parallel.
- Units 5 and 6 can run in parallel after Unit 4, provided they modify separate test and observability surfaces.
- Units 7 through 10 are sequential delivery gates.

## Risk

- **Highest-risk unit:** Unit 4, because applying the gate in the wrong route or middleware position could rate-limit unauthenticated requests, omit routes, or alter health/auth behavior.
- **Rollback plan:** Revert the isolated limiter service, route integration, and configuration addition in one commit. Existing authentication and routes remain intact.
- **Verification gate:** Run `verification-loop` after Unit 6, then `review-pr` before PR shaping.

## Hand-off after spec

The application source is absent from the supplied repository, so implementation cannot safely begin. Once the correct repository is available, start with Unit 1 to identify the existing storage and route/auth seams before selecting the concrete limiter adapter.

**Deviations:** No code or validators were run because this repository has no application files to change or validate.
