---
name: spec
description: Turn a fuzzy feature request into a concrete spec — acceptance criteria, scope boundaries, milestones — and decompose it into agent-sized units, each tagged with the recommended sagar droid for delegation. Use when starting new work, when given a vague request, or when "spec this out", "plan this", "decompose this", "break this down", or "let me think this through" appears in the task.
---

# Spec — Plan and Decompose

A repeatable flow for turning fuzzy work into a concrete, decomposable spec. Output is two things: a **spec** (what done looks like) and a **decomposition** (how to get there, agent-sized).

## When to Activate

- User says "spec this out", "plan this", "decompose this", "break this into steps", "give me a spec for", "let me think this through".
- A new feature, refactor, or migration is being scoped.
- A request is ambiguous and needs concrete shape before any code is written.
- Multiple things could be done — you need to decide which thing first.

## When NOT to Activate

- Task is concrete and ≤ 1 step. Just do it.
- Task is research / understanding (delegate to `deep-understanding` or `deep-research`, not this skill).
- Task is reviewing a diff already in flight (delegate to `change-review`).
- Task is fixing an obvious bug with a single-file scope.

## Procedure

### Phase 1 — Clarify the request

Restate the user's request in your own words in 1–2 sentences. Surface ambiguity:
- What's the desired end state?
- What's explicitly out of scope?
- What constraints are immovable (deadline, runtime, dependency, compliance)?

If anything is unclear, **ask one focused question** before continuing. Do not invent answers.

### Phase 2 — Write the spec

Output a spec in this exact shape:

```
## Spec

**Goal:** <1-sentence outcome>

**Acceptance criteria:**
- <observable, testable bullet>
- <observable, testable bullet>
- ...

**Out of scope:**
- <thing we are explicitly NOT doing>
- ...

**Constraints:**
- <runtime, dependency, security, perf, deadline, etc.>
- ...

**Open questions:**
- <unresolved items the user should answer before execution>
- ...
```

A criterion is "acceptance" only if a teammate could read it and write a test for it. "Make it fast" is not a criterion. "Renders the dashboard in <500ms p95 with 1000 rows" is.

### Phase 3 — Decompose into agent-sized units

Apply the **15-minute unit rule**:
- Each unit is independently verifiable.
- Each unit has a single dominant risk.
- Each unit has a clear "done" condition.

Output the decomposition in this exact shape:

```
## Decomposition

| # | Unit | Done condition | Recommended droid | Reason |
|---|------|----------------|-------------------|--------|
| 1 | <verb-phrase> | <observable> | `quick-analysis` / `deep-understanding` / `deep-research` / `change-review` / `security` / `pr-describer` / `commit-message-writer` / `prompt-optimizer` / `doc-generator` / `worker` (built-in) / `<self>` | <one line> |
| 2 | ... | ... | ... | ... |
```

Use the droid mapping table below.

### Phase 4 — Sequence and dependencies

Number the units in execution order. Note dependencies:

```
## Sequence
1. (Unit 1)
2. (Unit 2 — depends on 1)
3. (Unit 3 — independent of 1–2; can run in parallel)
4. ...
```

Identify parallelizable units explicitly so the user can fan out work.

### Phase 5 — Risk and exit criteria

```
## Risk
- **Highest risk unit:** <#> — <why>
- **Rollback plan:** <how to undo if a unit fails partway>
- **Hand-off after spec:** "Run unit 1 by delegating to <droid>", or "I will execute units 1-3 inline; delegate unit 4 to <droid> when ready."
```

## Droid Mapping (sagar-plugins)

| Unit shape | Recommended droid | Plugin |
|---|---|---|
| Repo is unfamiliar; need stack/structure | `quick-analysis` | investigation |
| Need architecture/agentic-config understanding | `deep-understanding` | investigation |
| Need external research (library docs, CVE, best practices) | `deep-research` | investigation |
| Diff staged; needs correctness review | `change-review` | review |
| Auth / consent / secrets / data exposure concern | `security` | review |
| Diff ready; need PR description | `pr-describer` | synthesis |
| Need a Conventional Commits message | `commit-message-writer` | synthesis |
| Audit a droid/skill prompt | `prompt-optimizer` | meta |
| Apply audit findings to agentic-config files | `doc-generator` | meta |
| Implement code (no specialized droid fits) | `worker` (Factory built-in) | — |
| Procedural step the main agent runs inline (e.g. "write the failing test", "set up the file structure") | `<self>` (main agent) | — |

If a unit fits no droid cleanly, recommend `<self>` and the user runs it inline.

## Companion Skills

After authoring a spec:
- `tdd-workflow` — implementing one of the decomposed units that needs new behavior
- `verification-loop` — running quality gates after a unit completes
- `coding-standards` — language-agnostic baseline for any code-writing unit

## Anti-Patterns

- **Vague acceptance criteria.** "Make X better" is not an acceptance criterion. Push for observable conditions.
- **Mega-units.** "Build the whole feature" is not a unit. Decompose until each unit fits the 15-minute rule.
- **No droid mapping.** Every unit gets a droid recommendation OR a `<self>` tag. No `TBD`s.
- **Inventing constraints.** Don't add "must use X technology" if the user didn't say so. Mark such things as Open Questions.
- **Skipping the spec to jump to decomposition.** The spec is what makes the decomposition reviewable.
- **Recommending droids that don't exist.** Stay in the mapping table above.
- **Speculative optionality.** Don't list "maybe also do X" in scope. If it's optional, it's out of scope until the user requests it.

## Edge Cases

- **Request is too small to spec** (single function fix): say so in one line, decompose into 1–2 units, skip the full spec template.
- **Request is too large to spec in one pass** (multi-quarter initiative): write a milestone-level spec and recommend the user run this skill again on each milestone individually.
- **Request is a research question**: hand off to `deep-research` or `deep-understanding`; this skill is not the right tool.
- **Spec touches multiple repos / services**: name them explicitly in Constraints; decompose per-repo and call out cross-service ordering.
- **User provides an existing spec**: validate it (acceptance criteria? out-of-scope? constraints?), point out gaps, then decompose.
- **User wants to skip spec and just decompose**: politely insist on the spec — decomposition without a spec is just task scattering.

## Output Template (use literally)

```
## Spec

**Goal:** ...

**Acceptance criteria:**
- ...

**Out of scope:**
- ...

**Constraints:**
- ...

**Open questions:**
- ...

## Decomposition

| # | Unit | Done condition | Recommended droid | Reason |
|---|------|----------------|-------------------|--------|
| 1 | ... | ... | ... | ... |

## Sequence
1. ...

## Risk
- **Highest risk unit:** ...
- **Rollback plan:** ...
- **Hand-off after spec:** ...
```

The user should be able to read this output and either approve, push back on a specific unit, or copy a single line and delegate it directly to the recommended droid.
