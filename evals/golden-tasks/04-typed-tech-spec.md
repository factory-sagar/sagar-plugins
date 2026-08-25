# Golden Task 04: Typed Tech Spec

Version: 2

## Target

`tech-spec`.

## Intent

The run exists to deliver a design-only typed handoff for saved-filter import and export that lets
implementers safely handle malformed input, unsupported versions, and deleted fields. Success
means a concrete, repository-aware design with alternatives, contracts, boundary parsing, failure
flows, call stacks, file ownership, and vertical RGR slices; an implementation-ready handoff
missing one non-critical flow remains partial achievement, while prose without contracts or an
invented implementation without design misses the point.

## Prompt

```text
We already decided to add import/export for saved filters. Users can export a saved filter to
JSON and import one later. Imports must reject malformed JSON, unknown versions, and filters that
reference deleted fields. Treat these product requirements as sufficient for Path A: write the
implementation-ready tech spec now, state repository-dependent details as assumptions or open
questions, and do not stop to ask for a repository path.
```

## Fulfillment

- Includes exact `Standards applied:` evidence naming only the topic docs or workflow that
  shaped this design.
- Includes current-state assumptions and marks unknowns as open questions.
- Compares at least two materially different design alternatives.
- Recommends one design after comparison.
- Defines typed contracts for exported payload, imported payload, parser result, accepted versions, and expected failures.
- Shows import and export call stacks from raw input through parsing, domain checks, adapter or persistence calls, and response projection.
- Includes failure flows for malformed JSON, unknown version, and deleted field references.
- Maps contracts and call-stack steps to files or modules.
- Provides vertical Red-Green-Refactor test slices.

## Boundaries

- Implement code.
- Trust imported JSON via unchecked casts.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
