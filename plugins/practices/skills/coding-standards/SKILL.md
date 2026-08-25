---
name: coding-standards
version: 1.4.0
description: |
  Standards router for modules, boundaries, failures, async ownership, tests, observability,
  naming, and type contracts. Invoke from design, implementation, and review when changed
  responsibilities need the user's shared engineering bar.
tags: [standards, code-quality, design, review, testing, architecture]
user-invocable: false
---

# Coding Standards

Use these standards while designing and editing code. They encode the user's taste: correctness first, boundary parsing, precise contracts, deep modules, typed failures, real-seam tests, explicit async ownership, and boring operational safety.

This skill is a router. Load the topic files that match the code you are touching. Do not treat this summary as the whole standard.

## Core tenets

- Correctness, safety, debuggability, boundary integrity, and test integrity come before convenience.
- Local conventions matter when they are compatible with these standards.
- Parse boundary input before it reaches core logic; pass refined values inward.
- Model invariants in types, constructors, parsers, and transitions.
- Keep expected failures visible in typed channels; reserve throws for defects and boundary translation.
- Design deep modules with intentional seams, small interfaces, and explicit dependencies.
- Verify observable behavior through real seams.
- Keep type contracts strict, local, documented, and boring.
- Improve changed paths without forcing broad migrations unless explicitly requested.
- Add backwards-compatibility, rollout, backfill, dual-write/read, or deployment sequencing work only when the user explicitly asks, so changed paths stay scoped to the requested behavior.

## Non-negotiables

- Untrusted, serialized, persisted, or framework-shaped input is parsed before core logic sees it, so core contracts retain runtime proof.
- Decoded data is refined through parsing rather than `as SomeType`, so serialized input cannot impersonate a domain value.
- Expected failures are visible in typed return channels, not hidden throws or rejected promises.
- Errors, logs, traces, metrics, snapshots, and panic summaries contain only safe values, preventing secret disclosure.
- Raw platform and framework bindings stay at composition seams or tightly local adapters, keeping core contracts portable.
- Service behavior receives explicit dependencies, time, randomness, and IDs, keeping it controllable and testable.
- Tests prove observable behavior through module interfaces or real seams rather than module mocks or method spies, preserving confidence through caller-visible contracts.
- Type escape hatches are local, justified with `SAFETY:`, and hidden behind precise interfaces, confining proof-obligation exceptions.
- Promises are owned: awaited, returned, collected, or handed to explicit detached-work machinery.
- Broad migrations require explicit user intent.

## How to apply the standards

1. Audit the local codebase before choosing a new pattern, library, adapter, schema style, error representation, test strategy, or module shape.
2. Classify the change by concern: modules, boundaries, errors, observability, async, tests, or type contracts.
3. Load every relevant topic file. The top-level summary is only the routing layer.
4. Apply safety standards before local convention. When local convention violates a non-negotiable, isolate compatibility at the boundary and improve the changed path.
5. Prefer the smallest coherent improvement. Do not start unrelated migrations or speculative abstraction.
6. Verify through the right seam. Tests should observe outcomes at the interface callers use.
7. Name trade-offs. If a standard cannot be fully applied without broad migration, state the constraint and the local improvement made.

## Topic routing

| If the change touches... | Load... |
|---|---|
| Shared standards terms, failure language, boundary vocabulary, module/runtime terminology | [`VOCABULARY.md`](VOCABULARY.md) |
| Names, booleans, file layout, cohesive modules, comments, generated or vendored code boundaries | [`NAMING_AND_LAYOUT.md`](NAMING_AND_LAYOUT.md) |
| Module depth, interfaces, seams, adapters, dependency ownership, functional core vs imperative shell | [`DESIGNING_MODULES.md`](DESIGNING_MODULES.md) |
| HTTP/RPC/queue/storage/env parsing, DTOs, codecs, projections, config | [`BOUNDARIES_AND_PARSING.md`](BOUNDARIES_AND_PARSING.md) |
| Expected failures, custom errors, not-found semantics, catch/classification | [`ERROR_HANDLING.md`](ERROR_HANDLING.md) |
| Tracing, logging, telemetry, redaction, safe summaries | [`OBSERVABILITY.md`](OBSERVABILITY.md) |
| Cancellation, promise ownership, concurrency, retries, transactions, workflows | [`ASYNC_AND_WORKFLOWS.md`](ASYNC_AND_WORKFLOWS.md) |
| Tests, properties, real seams, runtime verification, risk-matched evidence | [`TESTING_AND_VERIFICATION.md`](TESTING_AND_VERIFICATION.md) |
| Casts, `any`, readonly contracts, collections, optionality, exports, JSDoc, toolchain | [`TYPE_CONTRACTS.md`](TYPE_CONTRACTS.md) |

## Strong defaults

Use the repository's established choice when it exists and satisfies these standards. When no established choice exists, load the topic file that owns the concern and follow its strong defaults.

Do not treat this root file as enough context for boundary, error, async, testing, observability, or type-contract choices.

## Rejected framings

- "The existing code throws, so new expected failures can throw." Preserve compatibility at boundaries; do not copy unsafe contracts inward.
- "Validation is enough." Parsing must return the refined value and pass it inward.
- "A wrapper is architecture." A pass-through module earns its keep only when it hides complexity, owns policy, or translates across a real seam.
- "Mocks make tests isolated." Replace behavior through real seams.
- "Future flexibility justifies an interface." A seam is real when behavior varies, a boundary translates, or tests substitute through an intentional seam.
- "A lint suppression is a fix." Suppressions must be targeted and explain the safety invariant.
