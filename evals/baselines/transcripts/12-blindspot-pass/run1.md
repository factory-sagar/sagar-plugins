# Blindspot Pass: Per-User `/reports` Limiting

## Repository facts

- Rate limiting must live in middleware, not handlers. A prior handler-level implementation was reverted because it double-counted requests behind a proxy: [`docs/conventions.md:2-3`](/private/var/folders/r1/jxkxp7y512s9s3mzqbhs1c6r0000gn/T/golden-12-blindspot-pass.XNPY5q/docs/conventions.md#L2-L3).
- The current limiter is route-keyed: `rateLimit(route: string)` and `ROUTE_LIMITS` contains `/export`: [`src/middleware/rate-limit.ts:1-5`](/private/var/folders/r1/jxkxp7y512s9s3mzqbhs1c6r0000gn/T/golden-12-blindspot-pass.XNPY5q/src/middleware/rate-limit.ts#L1-L5).
- Every route is registered through `registerRoute`, which only receives `path` and a zero-argument handler, so no user identity is available at the current limiting seam: [`src/routes/register.ts:1-6`](/private/var/folders/r1/jxkxp7y512s9s3mzqbhs1c6r0000gn/T/golden-12-blindspot-pass.XNPY5q/src/routes/register.ts#L1-L6).
- `/reports` does not yet exist. New routes must be added to the repository route claim: [`AGENTS.md:1`](/private/var/folders/r1/jxkxp7y512s9s3mzqbhs1c6r0000gn/T/golden-12-blindspot-pass.XNPY5q/AGENTS.md#L1).
- The closest comparable implementation is `/export` in `ROUTE_LIMITS`, establishing centralized middleware configuration as the local pattern, but it establishes per-route behavior, not per-user behavior: [`src/middleware/rate-limit.ts:1-3`](/private/var/folders/r1/jxkxp7y512s9s3mzqbhs1c6r0000gn/T/golden-12-blindspot-pass.XNPY5q/src/middleware/rate-limit.ts#L1-L3).
- Tests are required by the repository contract (`AGENTS.md:1`), but the tracked tree has no test files or test-runner configuration.

## Premise contradiction

The requested per-user policy cannot be added strictly at the current limiter call site: it receives only a route string, with no authenticated principal or request context. This is architectural, so implementation should wait until identity ownership and propagation are decided.

## Questions to answer before building

1. **What canonical identity should define “user”, and where is it authenticated?**  
   Recommended answer: use the stable authenticated user ID, never IP address, bearer-token text, or a proxy-derived header. Specify the trusted component that validates credentials and supplies that ID.

2. **How should request context reach the middleware limiter?**  
   Recommended answer: make route registration and limiter invocation accept a validated request context containing `userId`, while keeping the decision in middleware. This preserves the existing no-handler-limit rule and avoids proxy double-counting.

3. **What exact policy applies to `/reports`?**  
   Recommended answer: specify a numeric limit, time window or token-bucket refill rate, burst capacity, scope (all report operations versus specific methods), and whether limits vary by plan or privileged users. Also define the retry behavior and response contract for a limit breach.

4. **What verification seam should be introduced?**  
   Recommended answer: add the repository’s chosen test harness and cover same-user exhaustion, independent quotas for two users on `/reports`, non-interference with `/export`, and rejection behavior. The current tracked repository provides no existing test framework to extend.

## Prompt-ready constraints

Include these in a future implementation prompt:

- Keep enforcement in `src/middleware`, never in route handlers.
- Do not key a user quota by proxy-visible request data.
- Preserve centralized route registration.
- Add `/reports` to the route claim.
- Add tests, as required by `AGENTS.md`.

## Deviations

Deviations: none.
