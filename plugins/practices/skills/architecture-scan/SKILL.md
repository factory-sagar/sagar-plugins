---
name: architecture-scan
version: 1.0.0
description: |
  Find standards-backed architecture refactor opportunities. Use when the user wants to scan a
  codebase, module, or feature area for higher-leverage refactors before writing a tech spec.
  Use when:
  - The user asks "where should this code live?" or "what should we refactor?"
  - A codebase needs architecture opportunities ranked before deeper design work
  - You want a brief for `tech-spec`, not implementation
tags: [planning, architecture, refactor, scan, review, standards]
---

# Architecture Scan

Scan a codebase for architecture improvement opportunities grounded in `../coding-standards/`. This is planning-only: do not edit code, run refactors, update docs, create ADRs, run tests, or run static checks unless the user explicitly asks after the scan.

The output is a globally ranked set of refactor candidates. Each candidate names the concrete friction, the standards areas involved, and the leverage the refactor would create.

## Principles

- Look holistically across the coding standards; do not privilege one lens such as deepening.
- Prefer architecture opportunities with concrete leverage: safer invariants, clearer boundaries, smaller caller burden, stronger locality, better test seams, clearer runtime ownership, or reduced duplicated policy.
- Evidence beats vibes. Every candidate needs concrete files, call paths, caller burden, duplicated behavior, leaked DTOs, bad seams, test contortions, or runtime friction.
- Do not estimate effort. Effort estimation is left to humans.
- Do not produce a tech spec. Prepare a brief for `../tech-spec/` when the user chooses a candidate.
- Do not design for backwards compatibility, migrations, rollout, backfill, dual-write/read paths, or deployment sequencing unless the user explicitly asks.

## 1. Establish scan scope

Use the user's explicit scope when provided: repo, directory, feature area, module, file set, or concern.

When no scope is provided:

1. Inspect the repository shape enough to understand size and major areas.
2. If the repository is small or the likely area is obvious from the prompt, scan that scope.
3. If the repository is large and the prompt gives no useful focus, ask one question to choose scope.

Do not ask for scope if code inspection can answer it.

Completion criterion: the scan scope is explicit, either from the user, inferred from repository structure, or chosen after one question.

## 2. Load standards and local context

Read the core standards:

- `../coding-standards/SKILL.md`
- `../coding-standards/VOCABULARY.md`
- `../coding-standards/DESIGNING_MODULES.md`
- `../coding-standards/BOUNDARIES_AND_PARSING.md`
- `../coding-standards/ERROR_HANDLING.md`
- `../coding-standards/TESTING_AND_VERIFICATION.md`

Load optional standards when the repository or scan scope touches them:

- `../coding-standards/OBSERVABILITY.md` for tracing, logging, telemetry, redaction, or safe summaries.
- `../coding-standards/ASYNC_AND_WORKFLOWS.md` for cancellation, promise ownership, concurrency, retries, idempotency, transactions, or workflows.
- `../coding-standards/TYPE_CONTRACTS.md` for casts, `any`, exported contracts, collection or object-shape friction, JSDoc, or toolchain architecture.

Read local context when present and relevant:

- `CONTEXT.md` or similar project domain-language files.
- ADRs near the scanned area.
- Existing modules, adapters, tests, parsers, error types, and entrypoints around the scan scope.

Completion criterion: the scan uses project vocabulary and loaded standards, and it does not suggest a new pattern before checking local precedent in the scanned area.

## 3. Inspect code only

Explore the codebase with file reads and search. Do not run tests, type checks, lint, formatters, package scripts, build commands, or static analysis commands as part of this skill.

If subagents or parallel exploration are available and the scan scope is broad enough, use them only to gather observations. The final candidate ranking and recommendations remain your synthesis.

Look for architecture friction across standards areas:

- domain invariants scattered across callers;
- missing or weak domain types, value classes, operation inputs, or state machines;
- boundary input that is validated but not parsed, repeatedly shape-checked, cast, or leaked inward;
- storage rows, protocol DTOs, or runtime-hop payloads crossing into application or domain modules;
- expected failures hidden as throws or rejections or broad error contracts;
- custom errors without stable tags or safe context;
- secrets, raw payloads, or unknown thrown values reaching diagnostics;
- pass-through modules, accidental interfaces, adapter sprawl, dependency bags, hidden globals;
- repeated orchestration or duplicated policy across entrypoints or callers;
- ambient time, randomness, IDs, resources, or platform bindings outside composition seams;
- missing cancellation propagation, floating promises, accidental sequential awaits, retry-unsafe mutation, or unclear workflow state;
- tests reaching past interfaces, using module mocks or spies, or forcing poor seams;
- type escape hatches, mutable exported contracts, unclear optionality, broad shapes, or object or projection hazards.

Completion criterion: each potential candidate is tied to concrete files, call paths, interfaces, tests, values, or runtime seams.

## 4. Form architecture candidates

A candidate is not a complaint. It is a refactor opportunity with a direction and expected leverage.

For each candidate, identify:

- the module, cluster, boundary, flow, or topology to improve;
- standards areas involved;
- concrete evidence of current friction;
- the refactor direction;
- what complexity, invariant, policy, parsing, error handling, orchestration, or runtime knowledge moves where;
- expected leverage, locality, safety, diagnosability, and testability gains;
- likely test strategy through real seams;
- recommendation strength: `Strong`, `Worth exploring`, or `Speculative`.

Use lightweight ASCII diagrams only when they clarify a call stack, seam, or before-or-after ownership better than prose.

Do not include effort estimates.

Completion criterion: every candidate has evidence, standards tags, a refactor direction, expected gain, test strategy, and recommendation strength.

## 5. Rank and prune

Rank candidates globally by architectural leverage, not by standards area.

Prefer candidates that:

- remove caller burden from multiple sites;
- make invalid states unconstructable or boundary trust explicit;
- concentrate policy, invariants, or orchestration in the module that owns them;
- replace implicit runtime or platform knowledge with explicit seams;
- improve behavior testing through public interfaces or real adapters;
- reduce repeated parsing, repeated error translation, repeated authorization, or repeated projection;
- close correctness, safety, observability, async, or runtime risks.

Downgrade or drop candidates that are:

- only aesthetic;
- speculative future flexibility;
- local cleanup with no architecture leverage;
- contradicted by a sound local convention;
- impossible to support with concrete evidence;
- really implementation work rather than architectural opportunity.

Completion criterion: the final list contains only candidates worth a human choosing to explore, with at most 5 candidates total.

## 6. Suggest context or ADR updates, but do not write them

If `CONTEXT.md` exists and the scan reveals stable domain language that should be named, suggest the exact term or clarification to add.

If a candidate conflicts with an ADR, mention the conflict only when current friction is concrete enough to justify revisiting the decision.

If the user rejects a candidate for a durable architectural reason that future scans would otherwise rediscover, suggest recording an ADR and summarize what it should capture.

Do not create or update `CONTEXT.md` or ADR files unless the user explicitly asks.

Completion criterion: documentation suggestions are specific and durable, not automatic artifact creation.

## 7. Present candidates and ask what to explore

Return candidate cards in globally ranked order. Tag each with standards areas. Include at most 5 candidates.

If no candidate clears the evidence threshold, say so directly. Summarize the scan scope, standards areas checked, and why no refactor should be pursued now. Do not manufacture a top recommendation.

Candidate card shape:

```md
### <Candidate title>: <Strong | Worth exploring | Speculative>

- **Standards areas:** Vocabulary and Types; Boundaries and Parsing; Designing Modules; ...
- **Files/modules:** `path`, `path`
- **Current friction:** <why the current architecture creates caller burden, risk, duplicated policy, poor seam, or test friction>
- **Evidence:** <concrete files, call path, repeated pattern, leaked representation, invalid state path, or test contortion>
- **Refactor direction:** <what changes at the architecture level; no full interface design yet>
- **Expected leverage:** <what callers, maintainers, tests, or runtime behavior gain>
- **Likely test strategy:** <how behavior would be verified through public interfaces or real seams>
- **Follow-up tech-spec should decide:** <interfaces, seams, contracts, call stacks, or open questions a tech spec must settle>
- **Context/ADR note:** <optional; only when durable>
```

If useful, add a small diagram:

```txt
Current:  Handler -> parse? -> raw DTO -> Service -> raw row -> callers branch
Proposed: Handler -> Parser -> Domain Input -> Service Module -> Adapter -> Result
```

End with:

```md
Top recommendation: <candidate title> - <why this has the best leverage>

Which candidate would you like to explore with a tech-spec brief?
```

Do not propose detailed final interfaces in the candidate scan unless a tiny sketch is necessary to explain the opportunity.

Completion criterion: the user can choose a candidate without needing a full implementation design.

## 8. When the user chooses a candidate

Do not write the tech spec inside this skill. Prepare a concise brief for `../tech-spec/` with:

- chosen candidate title;
- files or modules involved;
- problem and current friction;
- standards areas to load;
- known constraints and invariants;
- suspected seams, boundaries, adapters, and call stacks;
- evidence gathered;
- open questions;
- context or ADR suggestions, if any.

Then tell the user to run the tech-spec workflow on that brief.

If the chosen candidate needs more product, domain, or ownership decisions before a spec can be written, recommend a grilling session first with `../grill-me/`.

Completion criterion: the chosen candidate is handed off as a focused brief, not transformed into an implementation plan or code changes.

## Rejected framings

- "Architecture scan means deepening only." Deep modules are one lens; scan across all coding standards.
- "A candidate is a vibe." No evidence, no candidate.
- "Run the tests to see what's wrong." This skill inspects architecture; verification commands belong to other workflows.
- "Estimate effort." Humans estimate effort.
- "Write the spec now." Tech specs are owned by the tech-spec workflow.
- "Refactor while scanning." Scanning is planning-only.
- "Add migrations or backwards compatibility just in case." Target-state design is the default unless the user asks for migration planning.

## Self-Check (before returning)

1. Did I load the relevant coding-standards topics and local context?
2. Does every candidate have concrete file, call-path, value-flow, or test evidence?
3. Are there at most 5 candidates, globally ranked by leverage?
4. Did I include what a follow-up `tech-spec` should decide for each candidate?
5. If no candidate cleared the threshold, did I say that instead of inventing one?
6. Did I stay planning-only, with no edits, no test runs, and no implementation plan?
