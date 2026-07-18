# Golden Task 04: Typed Tech Spec

Version: 1

## Target

`tech-spec`.

## Prompt

```text
We already decided to add import/export for saved filters. Users can export a saved filter to
JSON and import one later. Imports must reject malformed JSON, unknown versions, and filters that
reference deleted fields. Treat these product requirements as sufficient for Path A: write the
implementation-ready tech spec now, state repository-dependent details as assumptions or open
questions, and do not stop to ask for a repository path.
```

## Expected behavior

The agent should produce a design-only typed handoff. It should include alternatives before choosing, concrete contracts, boundary parsing, failure types, call stacks, file map, and vertical RGR test slices.

## Must pass

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

## Must not do

- Implement code.
- Skip alternatives.
- Trust imported JSON via unchecked casts.
- Hide expected import failures as generic thrown exceptions.
- Ask the user to approve implementation by default.

## Score

- `pass`: all required handoff sections are present with concrete typed contracts.
- `partial`: the spec is implementation-ready but misses one non-critical flow.
- `fail`: the spec is prose-only, lacks contracts, or invents implementation without design.
