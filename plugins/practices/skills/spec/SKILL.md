---
name: spec
version: 1.0.0
description: |
  Turn a fuzzy feature request into a concrete spec (goal, acceptance criteria, scope, constraints,
  open questions) AND decompose it into agent-sized units, each tagged with the recommended sagar
  droid or worker for delegation. The starting point for any non-trivial new work.
  Use when:
  - User says "spec this out", "plan this", "decompose", "break this into steps"
  - User says "give me a spec for X", "let me think through", "draft a plan for", "scope this"
  - User says "what would it take to", "how should we approach X"
  - A new feature, refactor, or migration is being scoped
  - A request is ambiguous and needs concrete shape before any code is written
tags: [planning, decomposition, scoping, workflow, spec]
---

# Spec — Plan and Decompose

A repeatable flow that converts a fuzzy request into two artifacts the user can act on:

1. A **spec** — the definition of done. What must be true for the work to be complete, what's explicitly out of scope, what constraints we can't relax, and what's still unresolved.
2. A **decomposition** — the path from here to done. A numbered list of agent-sized units, each tagged with the right droid or worker to execute it, with explicit dependencies and parallelization opportunities.

The user should be able to read the output and either (a) approve the whole thing and run unit 1 immediately, or (b) push back on a specific unit, or (c) copy a single line of the decomposition and delegate it directly.

## When to Activate

- User says any of: "spec this out", "plan this", "decompose", "break this into steps", "give me a spec for", "draft a plan", "scope this", "let me think through", "what would it take to", "how should we approach", "outline what we need to do".
- A new feature, refactor, or migration is being scoped.
- A request is ambiguous and needs concrete shape before any code is written.
- Multiple paths are possible and you need to decide which one first.
- The user has dropped a long Slack message / issue / one-liner and you need to extract structure.

## When NOT to Activate

- Task is concrete and ≤ 1 step. Just do it directly.
- Task is purely understanding an existing system → **delegate to `deep-understanding`** (in the `investigation` plugin) instead.
- Task is a question with an external answer (library docs, CVE, best practice) → **delegate to `deep-research`**.
- Task is reviewing a diff already in flight → **delegate to `change-review`**.
- Task is fixing an obvious single-file bug with the cause already identified. Just write the fix.

## Procedure

The procedure has five phases. Several phases involve subtasks the main agent should **delegate** to a droid or to a fresh `worker` instance rather than do inline. Delegation keeps the main context clean and uses each model for what it's best at.

### Phase 1 — Clarify the request

Goal: understand the user's actual intent. Distinguish must-have from nice-to-have.

Inline (no delegation). Restate the request in your own words in 1–2 sentences. Then surface ambiguity by listing:

- **Desired end state**: when the work is done, what changed in the world?
- **Explicit non-goals**: what is the user NOT asking for?
- **Hard constraints**: what cannot move (deadline, runtime, dependency, compliance, customer expectation)?

If any of these are genuinely unclear (not just unstated, but ambiguous), **ask one focused question** before continuing. Do not invent answers. One question, not a list — the user is trying to delegate, not fill out a form.

### Phase 2 — Anchor in the existing system (delegate if needed)

Goal: ground the spec in what already exists. A spec written without knowing the system's current shape will miss constraints.

**Delegation rule:**
- If the user gave a path to a repo or said "in this codebase" and you have not seen it before → **delegate to `quick-analysis`** for a 60-second triage. Pass the repo path. Use the output to populate "constraints" in the spec.
- If the repo is non-trivial and the work spans subsystems → **delegate to `deep-understanding`** with focus questions like "where does <subsystem> live", "what conventions govern <area>", "what existing tests cover <feature>".
- If the question is about something external (a library's API, a known pattern, a CVE applicability) → **delegate to `deep-research`** with the focused question.
- If the system is already familiar (you've worked in it this session) → skip this phase.

Capture what comes back as a **"System anchor"** block in the spec. Cite file paths and droid session IDs so the user can re-open the investigation if needed.

### Phase 3 — Write the spec

Inline. Use this exact template:

```
## Spec

**Goal:** <1 sentence outcome — what changed in the world when this is done>

**Acceptance criteria:**
- <observable, testable bullet — a teammate could write a test from this>
- <...>

**Out of scope:**
- <thing we are explicitly NOT doing, with one-line reason>
- <...>

**Constraints:**
- <runtime / dependency / security / perf / deadline / compliance>
- <...>

**System anchor (from Phase 2):**
- <key facts about the current system relevant to this spec, with file:line if applicable>
- Source: <droid that gathered this, with session ID if delegated>

**Open questions:**
- <unresolved item the user should answer before execution>
- <...>
```

A line is "acceptance criteria" only if a teammate could read it and write a test from it. "Make it fast" is not acceptance criteria. "Renders the dashboard in <500ms p95 with 1000 rows on a M2 MacBook Pro" is.

A line is "out of scope" only if it would be a reasonable interpretation of the request but you're explicitly declining it. "Add a settings page" when the user asked for a button is out of scope. "Cure cancer" is not — nobody would expect it.

### Phase 4 — Decompose into agent-sized units

Goal: produce a numbered list of work where every entry is small enough to delegate cleanly and large enough to be a complete unit of progress.

Apply the **15-minute unit rule**:
- Each unit is independently verifiable (someone could run it and tell if it worked).
- Each unit has a single dominant risk (one thing that could break).
- Each unit has a clear "done" condition.

If a unit would take a focused engineer more than 15 minutes of actual implementation time (excluding investigation), decompose it further. If a unit is so small it's a one-liner ("rename variable X"), merge it with neighboring units.

Output as this exact table:

```
## Decomposition

| # | Unit | Done condition | Delegate to | Reason |
|---|------|----------------|-------------|--------|
| 1 | <verb-phrase, what gets done> | <observable signal> | <`droid-name` / `worker` / `<self>`> | <one-line why this delegate> |
| 2 | ... | ... | ... | ... |
```

Use the **Delegation Map** below to pick the right delegate per unit. Every unit gets a delegate — no `TBD`s.

### Phase 5 — Sequence, parallelization, and risk

Goal: tell the user what runs first, what can run in parallel, and what to watch for.

```
## Sequence

1. <unit #> — <one-line>
2. <unit #> — <one-line; depends on 1>
3. <unit #> — <independent of 1–2; can run in parallel with 2>
4. ...

## Parallelization opportunities

- Units <#> and <#> are independent → can be delegated simultaneously.
- Units <#> and <#> share input from unit <#> → must wait.

## Risk

- **Highest-risk unit:** <#> — <why this could go wrong>
- **Rollback plan:** <how to undo if a unit fails mid-flight>
- **Verification gate:** after unit <#>, recommend running `verification-loop` and handing diff to `change-review` before continuing.

## Hand-off after spec

Recommend the next action explicitly:
- "Approve this spec and I'll start by delegating unit 1 to `<delegate>`."
- OR: "Push back on any unit before I proceed."
- OR: "I'll run units 1–3 inline; delegate unit 4 to `<droid>` when ready."
```

## Delegation Map

For each unit shape, here's the recommended delegate. Use exact names — these are the sagar marketplace droids and the Factory built-in `worker`.

| Unit shape | Delegate | Plugin / origin | Why |
|---|---|---|---|
| Repo is unfamiliar; need stack/structure/entry points | `quick-analysis` | investigation | Fast triage, designed for this |
| Need architecture or agentic-config understanding | `deep-understanding` | investigation | Thorough, evidence-anchored |
| Need external research (library docs, CVE, best practices, comparisons) | `deep-research` | investigation | WebSearch + FetchUrl, source-tier hierarchy |
| Apply an approved change set (review findings, `debugger` fix plan, spec unit) | `implementer` | build | Minimal-diff discipline with targeted verification |
| Find untested behavior / write missing tests (incl. TDD RED) | `test-engineer` | build | Pins behavior; risk-ordered gap analysis |
| Root-cause a failing behavior before fixing it | `debugger` | investigation | Evidence-ranked hypotheses; hands fix plan to `implementer` |
| Implement open-ended feature work in code | `worker` | Factory built-in | General-purpose; main agent provides full context |
| Implement a feature using TDD discipline | `worker` + the `tdd-workflow` skill auto-loads | Factory built-in + practices plugin | Worker writes test first, then implementation |
| Run quality gates (build, type-check, lint, tests) | inline, guided by `verification-loop` skill | practices | Mechanical; the main agent can run commands directly |
| Strict pre-merge correctness review of a diff | `change-review` | review | Catches what tests miss |
| Security review (auth, consent, secrets, CVE-shaped) | `security` | review | STRIDE + OWASP lenses, CVE verification |
| Write a PR description for a diff | `pr-describer` | synthesis | Structured body with hand-off pointers |
| Write a Conventional Commits message | `commit-message-writer` | synthesis | Format-mechanical, fast |
| Audit a droid or skill prompt | `prompt-optimizer` | meta | Prompt-local quality, observed-output adherence |
| Apply audit findings to an agentic-config file | `doc-generator` | meta | Only droid with edit tools in this marketplace |
| Procedural step the main agent runs inline (e.g. "write the failing test" if main agent is the worker, "draft the spec body itself", "ask the user a question") | `<self>` | — | No delegation needed |

If a unit fits no droid cleanly, default to `worker` (Factory built-in) with a self-contained prompt — never invent a droid name.

## Worked Example

User request: "I need to add rate limiting to our API."

### Phase 1 output (clarify)

> Restating: add rate limiting to the API. Need to clarify before specifying — **what's the scope?** Per-endpoint, per-user, per-IP, or per-API-key? And **is this for abuse prevention, cost control, or fairness?**

(Ask one question; assume the answer is "per-API-key for cost control, all endpoints under /api/v1".)

### Phase 2 output (anchor — delegated)

> Delegating to `quick-analysis` on `/Users/sagar/code/factory/<repo>` to find the API framework, current middleware stack, and existing rate-limit infrastructure.
>
> Result (quick-analysis session abc123): Next.js 15 App Router, no current rate-limiter middleware, uses Upstash Redis already for caching, API keys validated in `lib/auth/api-key.ts:42`.

### Phase 3 output (spec)

```
## Spec

**Goal:** Every request to /api/v1/* enforces a per-API-key rate limit, returning 429 with Retry-After when exceeded.

**Acceptance criteria:**
- Each API key has a configurable per-minute and per-day budget (defaults: 60/min, 10000/day).
- A 429 response with Retry-After header is returned when either budget is exceeded.
- Rate-limit state survives server restarts (persisted in Redis).
- A test asserts that 61 requests in 60 seconds with the same key yields 1 success then 429s.
- Existing endpoints continue to function for under-quota traffic with <5ms p95 added latency.

**Out of scope:**
- Per-IP rate limiting (different problem, defer).
- A user-facing dashboard showing remaining quota (defer).
- Tiered budgets per API key plan (defer until pricing tiers exist).

**Constraints:**
- Must use the existing Upstash Redis instance (no new infra).
- Cannot break the existing auth middleware order.

**System anchor (from Phase 2):**
- API framework: Next.js 15 App Router; routes under `app/api/v1/`.
- API-key validation lives at `lib/auth/api-key.ts:42`; current middleware order is auth → handler.
- Redis client is `lib/redis.ts:10` (Upstash); already used for response cache.
- Source: `quick-analysis` session abc123.

**Open questions:**
- Should health checks (`/api/v1/health`) be exempt from rate limiting? (recommend: yes)
```

### Phase 4 output (decomposition)

```
## Decomposition

| # | Unit | Done condition | Delegate to | Reason |
|---|------|----------------|-------------|--------|
| 1 | Confirm Upstash Redis rate-limit library options and pick one (Upstash `@upstash/ratelimit`, custom sliding-window, etc.) | Decision recorded with rationale | `deep-research` | External library evaluation; not in the repo |
| 2 | Add `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_PER_DAY` env vars with documented defaults to `.env.example` | Both vars present and documented | `worker` | One-file, mechanical |
| 3 | Implement `lib/rate-limit.ts` with sliding-window logic against Redis, exposing `checkRateLimit(apiKey)` returning `{ allowed, remaining, resetAt }` | Unit tests pass for: under-quota, at-quota, over-quota, multi-window cases | `worker` + `tdd-workflow` skill | New module with clear acceptance criteria; TDD discipline applies |
| 4 | Wire `checkRateLimit` into the existing API middleware after auth, returning 429 with Retry-After when not allowed | Integration test: 61 requests in 60s yields 1×200 + 60×429 with Retry-After header | `worker` | One-file integration |
| 5 | Add exemption for `/api/v1/health` | Test asserts /health responds 200 even past quota | `worker` | Trivial wire-up |
| 6 | Run quality gates (build, type-check, lint, all tests with coverage) | All four phases green | `<self>` guided by `verification-loop` skill | Mechanical; main agent runs commands |
| 7 | Strict pre-merge review of the full diff | Reviewer assessment: `correct` or `needs changes` resolved | `change-review` | Catches what tests miss |
| 8 | Security pass: confirm rate-limit bypass paths, key-leakage in 429 responses, Redis-side DoS resistance | Reviewer assessment: `no blockers` | `security` | Auth-adjacent change |
| 9 | Write PR description with what / why / testing / breaking changes / follow-ups | PR body ready to paste | `pr-describer` | Structured prose synthesis |
| 10 | Write Conventional Commits message for final squash | Message ready | `commit-message-writer` | Format-mechanical |

## Sequence

1. Unit 1 (research) — kicks off in parallel with anything else.
2. Unit 2 (env vars) — independent of 1; can run in parallel.
3. Unit 3 (core lib) — depends on 1 (need the library decision).
4. Unit 4 (middleware wire-up) — depends on 3.
5. Unit 5 (health exemption) — depends on 4.
6. Unit 6 (verification) — depends on 5.
7. Units 7 + 8 (change-review + security) — both depend on 6; can run in parallel.
8. Unit 9 (PR description) — depends on 7+8 (so the body can include their findings).
9. Unit 10 (commit message) — depends on 9.

## Parallelization opportunities

- Units 1 and 2 run in parallel (5 min saved).
- Units 7 and 8 run in parallel (saves the full duration of whichever is slower).

## Risk

- **Highest-risk unit:** 4 — wiring rate limiting into the auth middleware chain is the spot most likely to break existing endpoints if middleware order is wrong.
- **Rollback plan:** units 3–5 are additive (new files + one middleware addition); revert with a single revert commit. Env vars (unit 2) are non-breaking.
- **Verification gate:** unit 6 (`verification-loop`) must pass before units 7+8 fire.

## Hand-off after spec

Approve this spec and I'll start by **delegating unit 1 to `deep-research`** and **unit 2 to `worker`** in parallel.
```

## Anti-Patterns

- **Vague acceptance criteria.** "Make X better" is not a criterion. Push for an observable condition a test can assert.
- **Mega-units.** "Build the feature" is not a unit. Decompose until each unit fits the 15-minute rule.
- **No delegate assigned.** Every unit gets a delegate from the table OR `<self>`. No `TBD`s, no "we'll figure it out".
- **Inventing constraints.** Don't write "must use X technology" if the user didn't say so. Constraints go in **Open Questions** until confirmed.
- **Skipping the spec to jump to decomposition.** The spec is what makes the decomposition reviewable. Without it, the decomposition is just task scatter.
- **Recommending droids that don't exist.** Stay within the Delegation Map. If something needs a droid we don't have, recommend `worker` with a self-contained prompt.
- **Speculative optionality.** Don't list "maybe also do X" in scope. Optional is out of scope until requested.
- **Front-loading research that isn't on the critical path.** If Phase 2 anchor delegation would block the spec writing AND the spec doesn't actually need that information, skip it.
- **Decomposing past usefulness.** A 1-line unit ("rename X") is too small — merge it with the next unit.
- **Forgetting verification and review.** Every spec for code changes ends with `verification-loop` then `change-review` (and `security` if relevant) before PR-shaping. Don't omit these.

## Edge Cases

- **Request is too small to spec** (single-function fix, typo, doc edit): say so in one line, optionally produce a 1–2 unit decomposition, skip the full spec template.
- **Request is too large to spec in one pass** (multi-quarter initiative, "rewrite the platform"): produce a **milestone-level** spec — each acceptance criterion is itself a milestone-sized goal. Recommend the user run this skill again on each milestone individually. Do not try to decompose a quarter into 15-minute units in one pass.
- **Request is actually a research question** ("what's the best way to..."): hand off to `deep-research` (external) or `deep-understanding` (in-repo). This skill is not the right tool; say so politely.
- **Request is actually a bug report** ("the dashboard is broken"): the first unit is investigation, not implementation. Phase 2 anchor delegation is the entire first step; the spec emerges from what's found.
- **Spec touches multiple repos or services**: name them explicitly in Constraints. Decompose per-repo. Call out cross-service ordering and any deployment-coupling (database migration must precede code, etc.) under Risk.
- **User provides an existing spec**: validate it (acceptance criteria observable? out-of-scope explicit? constraints captured?), point out gaps, then decompose. Don't rewrite the spec — annotate it.
- **User wants to skip the spec and just decompose**: politely insist on the spec. Decomposition without a spec is task scattering — the units have no shared definition of done. Offer to make the spec one paragraph if speed matters more than rigor.
- **You can't pick a delegate for a unit because the work doesn't fit anything in the Delegation Map**: default to `worker` and write a self-contained prompt in the "Reason" column. Don't invent a droid.
- **Decomposition has > 12 units**: the spec is probably too broad. Either consolidate units that share a delegate, or split the spec into two specs (milestone 1 spec + milestone 2 spec).
- **Phase 2 anchor delegation returns "the repo is unfamiliar even to me" from `quick-analysis`**: that's a finding. Add a unit at position 1 of the decomposition: "Run `deep-understanding` on the target subsystem before any implementation."

## Self-Check (before returning)

1. Does the spec have observable acceptance criteria (test-writable)?
2. Are Out of Scope items the kind a reasonable reader might assume IN scope?
3. Are Constraints distinguishable from preferences?
4. Is every Open Question one the user can answer in <5 minutes?
5. Does every decomposition unit have a delegate from the Delegation Map?
6. Does the decomposition end with `verification-loop` → `change-review` (+ `security` if relevant) → `pr-describer` → `commit-message-writer` for any code-shipping spec?
7. Is the "Hand-off after spec" line concrete (names which units, names which delegates)?

If any answer is no, fix before returning.
