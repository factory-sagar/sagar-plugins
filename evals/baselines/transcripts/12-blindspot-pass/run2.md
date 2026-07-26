# Blind-spot Pass: `/reports` Per-user Rate Limiting

## Territory constraints

- Rate limiting is centralized in the route middleware path: `registerRoute` calls `rateLimit(path)` before invoking every handler. The current interface has only a route path, not an authenticated user identity. [`src/routes/register.ts:3-5`](src/routes/register.ts#L3-L5), [`src/middleware/rate-limit.ts:4-5`](src/middleware/rate-limit.ts#L4-L5)
- Handlers must not enforce limits. A prior per-handler approach was reverted because it double-counted proxy requests. [`docs/conventions.md:2-3`](docs/conventions.md#L2-L3)
- The existing configurable precedent is route-scoped only: `/export` has a numeric limit in `ROUTE_LIMITS`. [`src/middleware/rate-limit.ts:1-3`](src/middleware/rate-limit.ts#L1-L3)
- Adding `/reports` requires updating the repository's machine-readable route claim, which currently lists only `/export`. [`docs/conventions.md:4`](docs/conventions.md#L4), [`AGENTS.md:1`](AGENTS.md#L1)
- Tests are a declared repository requirement, but no test runner or test files are currently tracked. [`AGENTS.md:1`](AGENTS.md#L1)

## Historical decision and calibration

The strongest comparable implementation is `/export`: its limit is configured in middleware, while registration remains generic. [`src/middleware/rate-limit.ts:1-3`](src/middleware/rate-limit.ts#L1-L3) The documented failed alternative is handler-level limiting, specifically due to proxy double counting. [`docs/conventions.md:2-3`](docs/conventions.md#L2-L3)

## Unknown unknowns to resolve before implementation

1. **What is the authoritative, verified user identity at the middleware boundary, and how are unauthenticated requests handled?**  
   The current limiter receives only `route`, so per-user limiting requires an identity-bearing contract rather than another `ROUTE_LIMITS` entry. [`src/routes/register.ts:3-5`](src/routes/register.ts#L3-L5)  
   **Recommended answer:** key by a verified stable user ID supplied before rate-limit middleware; explicitly choose a separate anonymous policy rather than falling back silently to proxy-derived identity.

2. **Where is the limiter state stored, and must it be shared and atomic across application instances?**  
   The existing limiter is elided and exposes neither state nor a storage/configuration contract. [`src/middleware/rate-limit.ts:4-5`](src/middleware/rate-limit.ts#L4-L5)  
   **Recommended answer:** state the deployment model first, then require a shared atomic backend if `/reports` can be served by multiple processes or hosts.

3. **What exact policy should apply to `/reports`?**  
   The repository shows a token-bucket intent and a single numeric `/export` setting, but does not define refill rate, burst capacity, report cost, or rejection behavior. [`src/middleware/rate-limit.ts:1-3`](src/middleware/rate-limit.ts#L1-L3)  
   **Recommended answer:** specify requests-per-user, refill/window, burst, whether report generation has a higher cost, and the expected HTTP status plus retry metadata.

4. **What testable route contract should `/reports` satisfy?**  
   The project requires tests and route claims, while the current registration function throws a generic rate-limit error. [`AGENTS.md:1`](AGENTS.md#L1), [`src/routes/register.ts:3-5`](src/routes/register.ts#L3-L5)  
   **Recommended answer:** require tests proving same-user exhaustion, user isolation, anonymous behavior, and the proxy-safe single enforcement path, plus update the route claim to include `/reports`.

## Implementation boundary

Do not implement this as a per-handler check or as a `/reports` entry in `ROUTE_LIMITS` alone. Both would contradict the middleware-only convention or fail to introduce the user identity required by the requested behavior.

**Deviations: none.** No files were changed.
