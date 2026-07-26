# Blindspot Pass: Per-User `/reports` Rate Limiting

## Repository reality

- The only current route claim is `/export`; adding `/reports` requires updating `AGENTS.md:1`.
- Rate-limit enforcement must remain in middleware. A prior per-handler approach was reverted after proxy-induced double counting, per `docs/conventions.md:2-3`.
- The existing limiter is route-keyed: `ROUTE_LIMITS` is keyed by path and `rateLimit(route)` only receives a route string (`src/middleware/rate-limit.ts:3-4`).
- Route registration also only passes a path to the limiter, while handlers receive no request or identity context (`src/routes/register.ts:3-5`).
- `/export` is the sole comparable configuration and establishes the current per-route override convention (`src/middleware/rate-limit.ts:3`).

## Premise contradiction

A direct extension of `ROUTE_LIMITS` cannot meet the per-user requirement: no present middleware or registration contract provides a user identity (`src/middleware/rate-limit.ts:4`, `src/routes/register.ts:3-4`).

**Proposed alternative:** resolve an identity-aware middleware boundary and a durable limiter-key/state model before designing `/reports`. Do not adapt the handler, since that violates the documented convention and prior proxy failure.

## Questions to answer before implementation

1. **What is the canonical, authenticated user identity available at middleware time?**  
   Recommended answer: a stable internal user ID, never an IP address, display name, or unverified request header.

2. **What quota policy should apply to `/reports`?**  
   Specify requests per user, window or token-bucket refill rate, burst capacity, and whether all report variants share the same budget.  
   Recommended answer: define an explicit token-bucket policy, consistent with the existing limiter’s stated model (`src/middleware/rate-limit.ts:1`).

3. **Where does per-user limiter state live, and what scope must it cover?**  
   Decide in-process versus shared storage, including behavior across multiple instances, restarts, and deployments.  
   Recommended answer: use shared, atomic state if `/reports` can be served by more than one process or host.

4. **How should unauthenticated, missing-identity, or malformed-identity requests behave?**  
   Recommended answer: reject them through the established authentication/middleware path rather than assigning a shared anonymous quota that could create collateral denial of service.

## Deviations

Deviations: none.
