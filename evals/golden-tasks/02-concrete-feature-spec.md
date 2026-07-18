# Golden Task 02: Concrete Feature Spec

## Target

`spec`.

## Prompt

```text
Spec out adding per-API-key rate limiting to all /api/v1 routes in this repo. Defaults should be 60 requests per minute and 10,000 requests per day. Health checks should be exempt. Use whatever rate-limit storage already exists in the repo if there is one.
```

## Expected behavior

The agent should produce a concrete scope and decomposition. It should inspect the repo or delegate repo anchoring before naming concrete files or storage choices.

## Must pass

- Outputs a `Goal` that describes observable behavior.
- Lists test-writable acceptance criteria, including both minute and day limits, health-check exemption, 429 behavior, and `Retry-After` where applicable.
- Lists out-of-scope items that a reasonable reader might assume, such as dashboards or per-IP limits.
- Captures constraints and open questions separately.
- Includes a system-anchor step from repo inspection or delegation before asserting existing storage.
- Decomposes the work into agent-sized units with a delegate for each unit.
- Ends with verification, `change-review`, optional `security`, `pr-describer`, and `commit-message-writer` handoff.

## Must not do

- Pick Redis, Upstash, D1, Postgres, or any other storage without repo evidence.
- Produce implementation code.
- Leave any decomposition row with `TBD` or no delegate.
- Treat security review as optional if auth, keys, or rate limits are touched.

## Score

- `pass`: all must-pass assertions are met and no must-not-do assertion appears.
- `partial`: the spec is concrete but misses one non-critical handoff.
- `fail`: the spec invents infrastructure or lacks a decomposed execution plan.
