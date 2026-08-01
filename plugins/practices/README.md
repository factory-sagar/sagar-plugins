# practices

> One public planning workflow backed by model-invoked design and engineering policy.

`spec` is the only public entry point. Short prompts receive the standard planning method;
detailed design intent automatically adds unknown discovery, grilling, architecture scan,
typed technical design, standards, TDD, and verification as required.

## Droid

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `planner` | Evidence-backed decisions, alternatives, units, sequencing, and open questions. | `gpt-5.6-sol` | `xhigh` | read-only + `Execute` |

Skills differ from droids: a skill is a procedure the main agent runs inline (auto-loaded when its description matches your task), while a droid is a sub-agent you delegate to. The skills here recommend delegating to sagar droids at the right moments.

## Install

```bash
droid plugin install practices@sagar-plugins
```

The `spec` skill registers `/spec <task>` as the guaranteed entry for "spec this out" — typing it runs the skill directly, no description matching involved.

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `spec` | "spec this out", "plan this", "decompose", "break this down", "let me think this through" | Turns a fuzzy request into a concrete spec (acceptance criteria, scope, constraints) and decomposes it into agent-sized units, each tagged with the recommended sagar droid. The starting point for non-trivial work. |
| `tech-spec` | "write a tech spec", "architecture handoff", "design this in detail", "call-stack design" | Writes a typed call-stack architecture handoff with alternatives, interfaces, seams, boundaries, adapters, and an RGR TDD plan. |
| `architecture-scan` | "architecture scan", "what should we refactor?", "where should this code live?" | Ranks standards-backed refactor candidates and prepares a brief for `tech-spec`. |
| `grilling` | "grill this plan", "stress-test this design", "poke holes in this" | Interviews the user one question at a time to sharpen the plan, with a recommended answer for each question. |
| `discovering-unknowns` | "blindspot pass", "unknown unknowns", "what am I missing?", "help me prompt better" | Map-territory discipline: blind-spot pass for unfamiliar areas, interview and brainstorm patterns for taste-shaped criteria, the shared Deviations contract for territory surprises mid-implementation, and an optional pre-merge quiz gate. |
| `agentic-engineering` | "AI-assisted work", "model routing", "session strategy", "AI code review checklist" | Thin router: routes completion, agent sizing, model complexity, evaluation, review, and prompt iteration to their owning workflows. |
| `tdd-workflow` | "TDD", "write tests first", "test-driven", "RED-GREEN-REFACTOR", "fix bug", "add feature" | Test-first discipline: RED checkpoint, GREEN checkpoint, optional REFACTOR. Loads the standards topics that govern tests, seams, async behavior, and observability. |
| `coding-standards` | "coding standards", "code quality", "boundary parsing", "type contracts", "code review checklist" | Standards router that loads topic docs for modules, boundaries, errors, async workflows, testing, observability, and type contracts. |
| `verification-loop` | "verify", "quality gates", "pre-merge checks", "is this ready", "check before commit" | Four-phase quality gate: build, type-check, lint, tests with coverage. Loads the standards topics that set the verification bar, then hands review ownership to `review-pr`. |

## Usage

For the canonical cross-plugin routing contract, see [`docs/WORKFLOW.md`](../../docs/WORKFLOW.md).

`spec` remains the broadest entry point. Reach for `tech-spec` when an approved plan still needs typed contracts and call stacks, and `architecture-scan` when the real question is which refactor or ownership direction to pursue.

## Related plugins

- **[`investigation`](../investigation/)**: `spec`, `architecture-scan`, and `tech-spec` recommend `deep-understanding` and `deep-research` for investigation-shaped work.
- **[`review`](../review/)**: `verification-loop` and `tdd-workflow` hand review ownership to `review-pr`.
- **[`synthesis`](../synthesis/)**: once review passes, `pr-describer` and `commit-message-writer` complete the cycle.
- **[`meta`](../meta/)**: `agentic-engineering` recommends the `audit-and-apply-loop` skill and `doc-generator` for evolving the prompts of the agents you delegate to.
- **[`build`](../build/)**: `tdd-workflow` delegates RED to `test-engineer` and GREEN or REFACTOR to `implementer`.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.

## Notes

These are skills, not droids: each encodes a procedure the main agent runs inline, applied to the current context rather than delegated. `coding-standards` is now a router, so load the relevant topic docs instead of treating the root file as the whole standard.
