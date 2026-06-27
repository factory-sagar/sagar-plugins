# Designing Modules

Design deep modules: cohesive behavior behind low-burden interfaces at intentional seams. A module earns its keep when deleting it would push meaningful complexity into callers.

## Vocabulary

Shared module terms such as **Module**, **Interface**, **Implementation**, **Seam**, **Domain Module**, **Service Module**, **Adapter**, **External Adapter Module**, **Deep Module**, **Accidental Interface**, **Functional Core**, and **Imperative Shell** live in [`VOCABULARY.md`](VOCABULARY.md).

This file uses these local terms:

**Depth:** Caller leverage per unit of interface burden. Deep modules hide substantial behavior behind cohesive interfaces.

**Leverage:** What callers get when one interface gives them a lot of capability.

**Locality:** What maintainers get when behavior, invariants, bugs, and verification concentrate in one place.

## Apply this file

When designing or changing a module, check all touched concerns:

- depth and deletion test;
- interface burden;
- dependency category;
- existing adapter reuse or extension;
- functional core and imperative shell boundary;
- resource ownership.

The module-design pass is complete when each touched concern is either satisfied or named as a compatibility constraint.

## Deep vs shallow

Deep module:

```txt
┌─────────────────────┐
│  Small, cohesive    │  callers learn little
│  interface          │
├─────────────────────┤
│  Substantial        │  implementation owns policy,
│  implementation     │  sequencing, invariants
└─────────────────────┘
```

Shallow abstraction:

```txt
┌──────────────────────────────┐
│ Wide/pass-through interface  │ callers still learn everything
├──────────────────────────────┤
│ Thin forwarding wrapper      │ little policy or translation
└──────────────────────────────┘
```

Use the deletion test: if deleting the module makes complexity disappear, it was pass-through waste. If deleting it spreads complexity across callers, it was earning its keep.

## Domain Modules, Service Modules, and External Adapter Modules

Use the standards terms by responsibility:

- **Domain Module:** Owns a domain concept, invariant, value behavior, parser, predicate, transition, or pure decision. It belongs in the functional core and does not perform I/O or hide dependencies.
- **Service Module:** Owns a cohesive use case, workflow, or service capability. It composes domain modules and interfaces implemented by adapters through explicit dependencies, sequences effects, owns use-case policy, classifies dependency failures, and returns typed outcomes.
- **External Adapter Module:** Owns framework, protocol, persistence, runtime, SDK, or third-party translation and mechanics. It converts between external shapes and service or domain contracts, including inbound adapters such as HTTP, RPC, or queue handlers and outbound adapters such as storage, email, payment, or platform integrations.

A Service Module answers "what should this use case do next?" An External Adapter Module answers "how do we speak HTTP, SQL, Stripe, a queue, or another boundary?"

Despite the word "service," pure domain behavior that does not depend on external capabilities or sequence effects remains a Domain Module under these standards.

## Non-negotiables

- A module owns one cohesive capability, concept, or policy.
- A module interface provides leverage by hiding implementation choices, invariants, ordering, and incidental steps.
- Interfaces do not force callers to understand unrelated methods, raw DTOs, hidden side effects, nullable state bags, or implementation ordering that the module can own.
- Dependency-bearing modules accept dependencies through intentional seams rather than hidden globals.
- Modules depend on the smallest meaningful behavior they use.
- New service or domain designs compose behavior through modules and explicit dependencies rather than inheritance, except for framework-required or genuine substitutability cases.
- New libraries, patterns, adapters, service modules, and abstractions require a project convention audit first.
- Raw framework or platform bindings stay at composition seams or tightly local adapters.
- Entrypoints do not duplicate business or domain policy that should be shared across protocols.
- Domain logic and pure decisions live in a functional core without hidden I/O.
- The imperative shell owns I/O sequencing, persistence, external calls, telemetry, time, randomness, and dependency failure classification.

## Strong defaults

- Outside Effect-heavy code, use constructor injection for dependency-bearing modules.
- In Effect-heavy code, preserve the repo's established service and layer conventions rather than introducing a parallel dependency pattern.
- Avoid ad hoc `deps` bags passed through service calls; concentrate dependency ownership in a Service Module or composition root.
- Use narrow structural dependency types at the consuming Service Module.
- Service Modules depend on narrow, behavior-shaped interfaces they consume; External Adapter Modules implement those interfaces at composition seams.
- Reuse an existing External Adapter Module through a narrow interface when it already provides the needed behavior.
- Extend an External Adapter Module only when the new method fits its cohesive capability and changes for the same reason.
- Create a new External Adapter Module only when reuse or extension would create bad coupling or an accidental interface.
- Record a new production adapter or service-module decision in an ADR when it introduces a new external dependency, platform capability, persistence model, runtime boundary, or dependency-provisioning pattern. Skip the ADR for test-only fakes, one-file framework glue that translates no policy, or adding methods to an established cohesive adapter.
- Keep small ubiquitous generic helpers in `prelude.ts`; keep domain and service policy out of `prelude.ts`.
- Use parsed, domain-specific authorization inputs such as `AdminUser`, `Session`, `Principal`, `DeployCredential`, or `CommandActor`; avoid generic `AccessContext` unless it is established architecture or deliberate domain vocabulary.
- Inject or pass time, randomness, and ID generation when they affect service behavior.
- Use Web Crypto or the runtime equivalent for production randomness; do not use `Math.random()` for security, identifiers, sampling, fairness, or consequential user-visible outcomes.

## Interface design

Ask:

- Can the caller say what they want rather than orchestrate steps?
- Can the module own validation, parsing, retries, projections, or ordering?
- Can the dependency surface shrink to only what this module uses?
- Does the interface expose DTOs or platform details that belong behind an adapter?
- Would tests naturally exercise the same interface callers use?

Avoid exposing internal steps as public surface just because tests want them.

## Dependencies and seams

Prefer narrow dependency interfaces at the consumer:

```ts
type UsersForPasswordReset = {
  findActiveByEmail(email: EmailAddress): Promise<Result<ActiveUser, UserLookupError>>;
};

export class PasswordReset {
  constructor(private readonly users: UsersForPasswordReset) {}
}
```

A wider concrete adapter can still satisfy it:

```ts
export class PostgresUsers {
  findActiveByEmail(...) { ... }
  findById(...) { ... }
  updateProfile(...) { ... }
}
```

Avoid requiring a mega-repository because one concrete adapter happens to expose it.

Also avoid interface confetti:

```ts
interface FindUserByEmail {
  findActiveByEmail(email: EmailAddress): Promise<Result<ActiveUser, UserLookupError>>;
}
```

A one-method named interface is useful only when the seam is meaningful; do not create one for every class by habit.

## External Adapter Module and Service Module reuse audit

Before adding an adapter or service module, inspect existing ones:

1. Can an existing adapter satisfy the needed narrow dependency type as-is?
2. Would adding a method to an existing adapter preserve cohesion and change for the same reason?
3. Would a new adapter better represent a separate capability?
4. Can an existing service module own the orchestration without becoming less cohesive?

If a meaningful new adapter or service module remains, record what was checked and why reuse or extension did not fit.

## Dependency categories

Use the dependency category to choose the seam and test strategy:

1. **In-process:** Pure computation or memory. Merge or deepen freely and test directly through the module interface.
2. **Local-substitutable:** A local test substitute exists, such as SQLite, PGLite, or an in-memory filesystem. Use the local substitute; no external port at the module interface just for testing.
3. **Remote but owned:** Your own service across a network. Define a port at the seam; production uses a transport adapter, tests use an in-memory or fake adapter.
4. **True external:** Third-party services. Inject a port; tests use a fake adapter through that seam.

One adapter is a hypothetical seam. Two adapters, usually production plus test or two real runtimes, make it real.

## Functional core and imperative shell

Functional core contains:

- domain logic;
- parsers and smart constructors;
- state transitions;
- combinators and decisions.

It avoids:

- I/O;
- hidden dependencies;
- ambient time, randomness, or IDs;
- framework types;
- thrown expected failures.

Imperative shell contains:

- input parsing;
- effect sequencing;
- persistence and external calls;
- dependency failure classification;
- telemetry;
- time, randomness, IDs;
- entrypoint and adapter glue.

Entrypoints authenticate and parse. Shared authorization policy lives in domain or service behavior and receives a parsed, domain-specific authorization input like `AdminUser`, `Session`, `Principal`, `DeployCredential`, or `CommandActor`.

## Helpers and prelude

Shared helpers are small, stable, genuinely domain-independent, and reused. Use precise helper module names like `string-case.ts` or `array.ts`.

`prelude.ts` may hold tiny ubiquitous generic helpers or capabilities:

- `casesHandled`, `shouldNeverHappen`, `notYetImplemented`;
- `Redacted`;
- common `Result` helpers;
- `Clock`, `Random`, `IdGenerator` and default implementations;
- shared concurrency and cancellation helpers.

Do not put domain invariants, service policy, or miscellaneous convenience piles in `prelude.ts`.

## Resource ownership

Resource creation and cleanup belong in bootstrap, composition roots, imperative shell code, or managed runtime layers. Imported modules should not start servers, open connections, register handlers, read env, or perform I/O at import time except in true entrypoints.

Avoid mutable singletons. If a framework requires singleton-like behavior, isolate it at the boundary.

## Rejected framings

- "A Service Module per noun." A module is justified by cohesive behavior, not naming symmetry.
- "A repository per table." Persistence adapters expose service or domain capabilities, not raw table mirrors.
- "An interface for every class." Seams are for variation, translation, and real substitution.
- "Deps bags are flexible." Dependency bags spread ownership and hide module contracts.
- "The controller can own business policy." Entrypoints translate protocols; shared policy belongs in domain modules or service modules.
- "Math.random is fine for IDs." Consequential randomness uses crypto randomness behind an injectable capability.

## Review checklist

Use this as the final scan after applying the rules above; the rule source of truth remains in the relevant sections.

- Adding a new Service Module without checking existing Service Modules and External Adapter Modules.
- Passing raw framework `Request`, Cloudflare `Env`, database rows, or DTOs into Service Modules.
- Creating pass-through wrappers that only rename another API.
- Hiding `Date.now()`, `new Date()`, `crypto.randomUUID()`, or `Math.random()` in service logic.
- Exporting internal helpers to make tests easier.
- Putting domain policy in `utils.ts`, `helpers.ts`, or `prelude.ts`.
