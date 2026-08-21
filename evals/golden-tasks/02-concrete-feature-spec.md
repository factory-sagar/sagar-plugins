# Golden Task 02: Concrete Feature Spec

Version: 3

## Target

`spec`.

## Prompt

```text
Spec out adding per-API-key rate limiting to all /api/v1 routes in this repo. Defaults should be 60 requests per minute and 10,000 requests per day. Health checks should be exempt. Use whatever rate-limit storage already exists in the repo if there is one.
```

## Intent

The run exists to provide an execution-ready, repository-anchored plan for per-API-key rate
limiting, including the stated limits, exemption, response behavior, scope, and handoffs.
Success means a concrete decomposition grounded in repository evidence rather than assumed
infrastructure; an otherwise concrete plan that misses one non-critical handoff remains partial
achievement, while inventing storage or lacking an execution plan misses the point.

## Fulfillment

- Outputs a `Goal` that describes observable behavior.
- Lists test-writable acceptance criteria, including both minute and day limits, health-check exemption, 429 behavior, and `Retry-After` where applicable.
- Lists out-of-scope items that a reasonable reader might assume, such as dashboards or per-IP limits.
- Captures constraints and open questions separately.
- Includes a system-anchor step from repo inspection or delegation before asserting existing storage.
- Decomposes the work into agent-sized units with a delegate for each unit.
- Ends with a verification, `review-pr`, `pr-describer`, and `commit-message-writer` handoff. `review-pr` owns reviewer fan-out, so a separate `security` unit is not expected.

## Boundaries

- Pick Redis, Upstash, D1, Postgres, or any other storage without repo evidence.
- Produce implementation code.
- Skip the review stage entirely, or name a reviewer droid directly instead of handing review ownership to `review-pr`.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
