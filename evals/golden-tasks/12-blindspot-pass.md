# Golden Task 12: Blind-Spot Pass

Version: 2

## Target

`discovering-unknowns`.

## Setup

```bash
mkdir -p src/middleware src/routes docs
cat > src/middleware/rate-limit.ts <<'EOF'
// Global token-bucket limiter. All routes pass through this via registerRoute();
// per-route overrides belong in ROUTE_LIMITS, not in handlers.
export const ROUTE_LIMITS: Record<string, number> = { '/export': 2 };
export function rateLimit(route: string): boolean {
  return true; // elided
}
EOF
cat > src/routes/register.ts <<'EOF'
import { rateLimit } from '../middleware/rate-limit';
// Convention: handlers never check limits themselves (see docs/conventions.md).
export function registerRoute(path: string, handler: () => unknown) {
  if (!rateLimit(path)) throw new Error('rate limited');
  return handler;
}
EOF
cat > docs/conventions.md <<'EOF'
# Conventions
- Rate limiting lives ONLY in middleware. A previous per-handler attempt was reverted
  (2025-11): it double-counted requests behind the proxy.
- Every new route must be listed in AGENTS.md routes claims.
EOF
cat > AGENTS.md <<'EOF'
{ "domain": "api", "routes": ["/export"], "tests": true }
EOF
```

## Prompt

```text
I'm new to this codebase and I need to add per-user (not per-route) rate limiting for a new
/reports route. Do a blindspot pass: help me find my unknown unknowns with repo evidence,
and give me the questions I should answer before I prompt you to build it. Do not implement
anything.
```

## Intent

The run exists to equip a newcomer to design per-user `/reports` rate limiting with evidence from
this repository: the middleware-only convention and reverted handler approach, the AGENTS.md route
claim, and the mismatch between the per-route override seam and per-user identity. Success means
these constraints are cited with scratch-repo references and close with two to four
architecture-changing questions ordered by leverage; evidence-backed unknowns that miss the route
claim or leave the questions unordered are partial achievement, while implementation or generic
advice without repository evidence misses the point entirely.

## Fulfillment

- Cites the middleware-only rate-limiting convention AND the recorded revert of the per-handler approach as evidence (docs/conventions.md), not as generic advice.
- Flags that adding /reports requires updating the AGENTS.md routes claim.
- Identifies that per-user limiting does not fit the existing per-route `ROUTE_LIMITS` seam and raises where user identity would come from as an open question.
- Ends with 2-4 questions ordered by architectural leverage (identity source / storage of per-user state before naming details).
- Every claim carries a file reference from the scratch repo.

## Boundaries

- Write or edit any code or docs.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
