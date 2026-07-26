---
name: architecture-scan
version: 1.3.0
description: |
  Architecture scan for ownership, boundary, module, state, failure, and test-seam
  opportunities. Invoke when planning asks where code should live or whether an existing
  design should change before a typed technical specification.
tags: [planning, architecture, refactor, scan, review, standards]
user-invocable: false
---

# Architecture Scan

Scan existing code for evidence-backed refactor candidates. This is planning-only: do not edit,
refactor, update docs or ADRs, run tests, or run static checks. Do not estimate effort or add
migration, compatibility, rollout, backfill, or dual-read/write design unless requested.

Scan before planning when the request asks where code belongs, which refactor target has the best
leverage, or whether an existing design should change. Planning is enough when the target,
ownership, and implementation direction are already decided.

Load `../coding-standards/SKILL.md`, `VOCABULARY.md`, `DESIGNING_MODULES.md`,
`BOUNDARIES_AND_PARSING.md`, `ERROR_HANDLING.md`, and `TESTING_AND_VERIFICATION.md`; load type,
async, or observability guidance when relevant. Inspect local context, ADRs, entrypoints,
modules, adapters, parsers, errors, and tests before recommending a new pattern.

## Scope and evidence

Use explicit scope. Otherwise infer a focused scope from repository shape and the request; ask
one question only when a large repository has no credible focus. Read and search code only. Each
candidate needs concrete paths, call paths, leaked representations, repeated policy, invalid
state path, test contortion, or runtime seam. Evidence beats aesthetic preference.

## Scan questions

| Dimension | Ask these questions |
|---|---|
| **Ownership** | Who owns each invariant, policy, orchestration step, and runtime resource? Is that knowledge duplicated across callers or entrypoints? |
| **Boundary** | Where does untrusted input enter? Is it parsed once into canonical values, or do DTOs, rows, runtime payloads, casts, and shape checks leak inward? |
| **Module** | Does a module own a coherent capability with small caller burden, or is it a pass-through, dependency bag, accidental interface, or repeated orchestration? |
| **State** | Are valid states explicit in types or transitions? Can callers construct invalid combinations, mutate exported state, or lose lifecycle ownership? |
| **Failure** | Are expected failures typed, stable, and translated at boundaries? Can unknown throws, raw payloads, secrets, retries, cancellation, or idempotency violations escape? |
| **Test seam** | Can behavior be tested through a public interface and real adapter? Do mocks, spies, hidden globals, ambient time, or platform bindings reveal a missing seam? |

A candidate must identify the affected module, boundary, flow, or topology; standards areas;
current friction and evidence; refactor direction; knowledge that moves to its owner; expected
leverage; a real-seam test strategy; and `Strong`, `Worth exploring`, or `Speculative` strength.
Use a small ASCII flow only when it clarifies ownership or a boundary.

## Rank and hand off

Rank at most five candidates globally by leverage. Prefer changes that remove caller burden,
make invalid states unconstructable, concentrate policy, make boundary trust explicit, replace
implicit runtime knowledge with a seam, improve behavior testing, or eliminate repeated parsing,
translation, authorization, or projection. Drop aesthetic cleanup, unsupported claims, speculative
flexibility, and work contradicted by sound local convention.

```md
### <Candidate>: <Strong | Worth exploring | Speculative>

- **Standards areas:** <areas>
- **Files/modules:** <paths>
- **Current friction:** <concrete burden or risk>
- **Evidence:** <path, call path, repeated pattern, or test contortion>
- **Refactor direction:** <architecture change, not final interfaces>
- **Expected leverage:** <caller, safety, locality, or test benefit>
- **Likely test strategy:** <public interface or real seam>
- **Follow-up tech-spec should decide:** <contracts, seams, flows, and open questions>
- **Context/ADR note:** <only if durable>

Top recommendation: <candidate and why>
```

If no candidate clears the evidence threshold, say so and summarize scope and standards checked.
Do not manufacture a recommendation.

When the user selects a candidate, prepare a brief for `../tech-spec/`: title, paths, current
friction, evidence, standards, constraints, invariants, suspected seams and flows, open questions,
and any durable context or ADR note. Invoke `grilling` first if material product, domain, or
ownership decisions remain. Do not write the technical spec or implementation here.
