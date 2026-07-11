# Review Policy

The selector chooses lenses from changed responsibilities and operations. Languages and
frameworks are signals only; no language receives privileged review treatment.

## Mandatory

Apply every item to every changed behavior:

- **Intent and completeness**: the diff implements the stated outcome end to end.
- **Correctness and invariants**: boundaries, empty states, limits, ordering, and state
  transitions preserve caller-visible guarantees.
- **Tests and evidence**: changed behavior has a regression net through the real seam; tests
  fail when the behavior breaks and do not merely restate mocks.
- **Failures**: expected failures are classified and observable; defects are not swallowed
  or converted into misleading success.
- **Ownership and mutation**: every write has one owner; aliases, shared mutable state, and
  partial updates cannot violate invariants.
- **Async and workflow safety**: work is awaited, returned, collected, or explicitly
  detached; cancellation, retry, concurrency, and idempotency are handled where reachable.
- **Boundaries and contracts**: external values are parsed before core logic; protocol,
  persistence, and domain shapes do not leak across their owning boundary.
- **Scope and structure**: no drive-by behavior, duplicated policy, unearned abstraction,
  dead compatibility path, or weakened gate entered with the change.
- **Operations and rollback**: telemetry is truthful and safe; migrations, flags, and
  deployment changes have a credible recovery path.

## UI State and Reactivity

Use when a diff introduces effects, subscriptions, observers, reactive stores, lifecycle
hooks, event listeners, or derived UI state.

- Effects synchronize with external systems rather than derive render state.
- Derived values are computed from canonical state instead of mirrored.
- Subscriptions and listeners have symmetric cleanup and stable ownership.
- Dependency changes cannot create loops, stale closures, duplicate requests, or lost work.
- User-visible state remains consistent across loading, empty, error, and retry transitions.
- Accessibility, focus, keyboard behavior, and semantics survive the state change.

For React, load the installed `no-use-effect` policy when `useEffect`,
`useLayoutEffect`, or effect-shaped custom hooks appear. Equivalent constructs in other
frameworks receive the same questions.

## Mutation and State Ownership

Use when collections, caches, objects, records, transactions, files, or persisted state are
modified.

- Mutation does not escape its owner through aliases.
- Atomic changes cannot leave half-applied state.
- Updates preserve immutability contracts expected by observers or memoization.
- Cache writes and invalidation share one source of truth.
- Retries and duplicate delivery cannot apply a mutation twice.
- Rollback restores all coupled state, not just the first write.

## Authentication and Authorization

Use when sessions, identities, roles, tenants, permissions, tokens, API keys, or privileged
operations change.

- Authentication proves identity at the correct boundary.
- Authorization checks the fetched object, not only client-supplied scope.
- Tenant identity is carried through storage queries and side effects.
- Client-controlled roles, ownership, or scope are never trusted.
- Error differences do not expose cross-tenant existence.
- Audit records attribute the verified actor, resource, and tenant.

## External Input and Injection

Use when request data, CLI arguments, files, environment variables, webhooks, queries,
templates, URLs, or model inputs enter the system.

- Parsing establishes the canonical type and rejects non-finite, ambiguous, or oversized
  values.
- SQL, shell, template, path, URL, and prompt sinks do not interpolate untrusted content.
- Allowlists are applied at the owning boundary.
- Error output does not echo secrets, credentials, or sensitive payloads.
- Resource limits bound attacker-controlled work.

## Persistence and Migration

Use for schema, migration, serialization, storage, cache format, or durable workflow changes.

- Migration ordering is compatible with mixed application versions.
- Re-runs are idempotent and partial failures are recoverable.
- Destructive changes have explicit data-loss approval and rollback.
- Readers and writers agree on the canonical representation.
- Backfills are bounded, observable, resumable, and safe under concurrent writes.
- Constraints and indexes preserve rather than merely document invariants.

## Async, Concurrency, and Distributed Work

Use for promises, futures, threads, locks, queues, jobs, retries, transactions, or event
delivery.

- Every task has explicit ownership and cancellation behavior.
- Independent work is concurrent only when ordering is irrelevant.
- Shared state has an atomicity or serialization boundary.
- Retry policy distinguishes transient failure from permanent rejection.
- Commands are idempotent or deduplicated.
- Timeouts do not abandon state-changing work without reconciliation.
- Events are emitted only after the state they claim is committed.

## Dependencies and Supply Chain

Use for manifests, lockfiles, downloaded tools, build plugins, images, or generated code.

- The dependency is necessary and already-used alternatives were considered.
- Version source, integrity, lifecycle scripts, and transitive changes are understood.
- Major-version changes include contract and migration review.
- Downloaded or executed artifacts are pinned and use trusted transport.
- Known vulnerability claims are verified against NVD, GHSA, or vendor advisories.
- Lockfile changes correspond to source-manifest intent.

## Secrets, Privacy, and Observability

Use for credentials, configuration, logs, traces, metrics, analytics, PII, or customer data.

- Secrets exist only in approved secret stores and never in source fallbacks.
- Logs and errors use safe summaries and bounded cardinality.
- Metrics do not encode user or tenant identifiers in labels.
- Consent, retention, deletion, and access boundaries remain enforced.
- Success telemetry occurs after success; failure telemetry preserves the actual cause.
- Debug paths cannot expose production-sensitive content.

## Public Contracts and Compatibility

Use for APIs, SDKs, exported types, CLI surfaces, file formats, shared packages, or events.

- New required fields and removed behavior are explicit breaking changes.
- Optionality reflects real absence, not implementation convenience.
- Producers and consumers are updated together or have a deliberate transition.
- Errors and status codes remain stable where callers depend on them.
- Compatibility code exists only for a proven external boundary and has one owner.

## Performance and Resource Use

Use for loops, queries, render paths, large collections, network fan-out, caches, or hot
request paths.

- No new N+1, unbounded fan-out, repeated parsing, or quadratic operation is introduced.
- Memory, handles, listeners, and temporary files are released.
- Expensive work is bounded, cached, paginated, or moved off the critical path where
  appropriate.
- Performance claims carry measurements tied to a representative workload.
- Optimization does not weaken correctness, consistency, or observability.

## CI, Build, and Release

Use for workflows, build scripts, deployment configuration, permissions, or release tooling.

- Jobs are deterministic and safe to re-run.
- Permissions and credentials use the narrowest scope.
- Gates are not weakened, skipped, or given raised baselines to admit the diff.
- Cache keys cannot restore incompatible artifacts.
- Deployment and rollback operate on the same versioned artifact.
- Required checks represent the behavior the PR actually changes.

## Agentic Configuration

Use for prompts, skills, droids, MCP, hooks, automation, or model routing.

- Invocation descriptions distinguish the skill from adjacent workflows.
- Tool access is the minimum required for the role.
- Completion criteria are checkable and prevent premature completion.
- External content and tool results are treated as untrusted instructions.
- Model claims have current evaluation evidence.
- Hooks fail safely and cannot exfiltrate credentials or overwrite user work.
- Public artifacts contain no private session context.
