# Golden Task 12: Blind-Spot Pass

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

## Expected behavior

The pass searches the scratch repo, surfaces the territory constraints with `file:line`-style evidence (middleware-only convention, the reverted per-handler attempt, the AGENTS.md routes claim, ROUTE_LIMITS as the override seam), and closes with a small set of architecture-changing questions. No code is written.

## Must pass

- Cites the middleware-only rate-limiting convention AND the recorded revert of the per-handler approach as evidence (docs/conventions.md), not as generic advice.
- Flags that adding /reports requires updating the AGENTS.md routes claim.
- Identifies that per-user limiting does not fit the existing per-route `ROUTE_LIMITS` seam and raises where user identity would come from as an open question.
- Ends with 2-4 questions ordered by architectural leverage (identity source / storage of per-user state before naming details).
- Every claim carries a file reference from the scratch repo.

## Must not do

- Write or edit any code or docs.
- Produce a generic rate-limiting checklist without repo evidence.
- Recommend the per-handler approach the repo explicitly reverted.
- Ask ten questions at once or bury the architecture-changing ones.

## Score

- `pass`: evidence-backed unknowns including the revert and the AGENTS.md claim, closing with leverage-ordered questions.
- `partial`: evidence-backed unknowns but the closing questions are unordered or the AGENTS.md claim is missed.
- `fail`: implements anything, or returns generic advice without repo evidence.
