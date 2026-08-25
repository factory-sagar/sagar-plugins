---
name: tech-spec
version: 1.4.0
description: |
  Convert scoped design work into typed contracts, seams, adapters, call stacks, failure
  flows, file ownership, and vertical test slices. Invoke automatically when a plan carries
  architecture-changing boundaries or explicit technical-design intent.
tags: [planning, architecture, design, interfaces, call-stacks, tdd]
user-invocable: false
---

# Tech Spec

Produce an implementation-ready, typed call-stack handoff. Success means an executor can
implement the approved scope from concrete contracts, seams, flows, ownership, and vertical test
slices. Prefer TypeScript-like pseudocode where precision matters.

`spec` owns scope and decomposition. `architecture-scan` finds and ranks existing-design
opportunities before a target is chosen. This skill turns an approved scope or selected candidate
into contracts and flows. Invoke `grilling` first when material design context is absent.

Load `../coding-standards/SKILL.md`, its relevant topic documents, and
`../tdd-workflow/SKILL.md`; inspect local vocabulary and precedent before introducing a pattern,
library, adapter, schema, or test strategy.

## Boundaries

- Design only: do not implement; save a file only when requested.
- Mark unknown requirements, domain rules, contracts, and call-stack facts as open questions.
  Ground every claim in the conversation, code, docs, or an explicit open question.
- Add seams only when a real boundary, invariant, locality, leverage, or test benefit supports
  them.
- Include typed contracts, real seams, call stacks, and vertical test slices whenever applicable;
  return the spec inline by default.

## Choose the path

| Available context | Action |
|---|---|
| Problem, callers, constraints, affected code, and acceptance intent are established | Write the spec. Inspect the repository for answerable gaps. |
| Material problem, ownership, boundary, or constraint facts are missing | Invoke `grilling`. Ask one question at a time with a recommended answer, then use the resolved context for types, APIs, flows, and files. |

## Design method

1. Capture current state, problem, callers, goals, non-goals, invariants, constraints, affected
   systems, entrypoints, operational concerns, risks, and open questions.
2. Compare every credible, materially different alternative before recommending one. Alternatives
   differ in ownership, interface, seam placement, call stack, runtime topology, or module
   boundary, not merely names. Compare caller burden, invariant locality, boundary parsing,
   failures, real-seam testability, operational fit, and implementation complexity.
3. Specify each added, changed, or deleted domain value, refined type, state variant, input,
   output, request or response, function, module interface, expected failure, adapter, DTO,
   codec, projection, and public API.
4. Trace each changed behavior from entrypoint through parsing, canonical input, service, adapter,
   typed result or error, projection, and serialized response. Include current versus proposed
   flow where changing behavior and include authorization, cancellation, retry, transaction,
   idempotency, observability, or runtime hops when reachable.
5. Map every contract and call-stack step to an added, changed, or deleted file or module, test,
   config, migration, runtime artifact, or open question. State what that owner owns.
6. Plan Red-Green-Refactor vertical slices: one behavior test through a public interface or real
   seam, minimal implementation, then repeat. Cover proportionate happy paths, failures, parser
   rejection, invariants, state transitions, adapter contracts, runtime semantics, and
   high-consequence end-to-end behavior.

## Contracts and seams

A contract is typed only when it states the concrete values, fields, variants, input and output
shapes, error cases, and callable interface needed to reject invalid use. A named description or
unconstrained `object` is not a typed contract.

```ts
type CreateOrderInput = { customerId: CustomerId; lines: readonly OrderLine };
type CreateOrderResult = Result<Order, CreateOrderError>;
interface OrderRepository { save(order: Order): Promise<void> }
```

A seam is a dependency boundary that isolates a real framework, persistence, network, time,
randomness, telemetry, runtime, or platform concern. Put domain invariants and application
orchestration inside their owning modules; put translation at the boundary in adapters. Name the
adapter, implementation, values crossing it, what each side may know, and what must not leak.

## Required output

```md
# <Title>

## Summary
## Context / Current State
## Goals
## Non-Goals
## Invariants
## Design Constraints
Standards applied: <only documents that shaped this design>

## Alternatives Considered
### Option N: <materially different design>

## Recommendation
## Proposed Design
## Domain Model and Types
## Types, Interfaces, and APIs
## Seams, Boundaries, Adapters, and Implementations
## Call Stacks and Data Flow
### Current / Old Flow
### Proposed / New Flow
### Failure Flow
### Retry / Cancellation / Idempotency Flow
### Observability Flow

## Files to Add / Change / Delete
## RGR TDD Test Plan
## Risks and Open Questions
```

Omit only genuinely inapplicable sections.
