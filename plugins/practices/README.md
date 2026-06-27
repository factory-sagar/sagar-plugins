# practices

> Planning and engineering-discipline skills: scope, stress-test, design, set standards, test, and verify.

Nine repeatable flows auto-load when your task matches. Together they cover the loop from a fuzzy idea to a standards-backed, gate-ready change.

Skills differ from droids: a skill is a procedure the main agent runs inline (auto-loaded when its description matches your task), while a droid is a sub-agent you delegate to. The skills here recommend delegating to sagar droids at the right moments.

## Install

```bash
droid plugin install practices@sagar-plugins
```

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `spec` | "spec this out", "plan this", "decompose", "break this down", "let me think this through" | Turns a fuzzy request into a concrete spec (acceptance criteria, scope, constraints) and decomposes it into agent-sized units, each tagged with the recommended sagar droid. The starting point for non-trivial work. |
| `tech-spec` | "write a tech spec", "architecture handoff", "design this in detail", "call-stack design" | Writes a typed call-stack architecture handoff with alternatives, interfaces, seams, boundaries, adapters, and an RGR TDD plan. |
| `architecture-scan` | "architecture scan", "what should we refactor?", "where should this code live?" | Ranks standards-backed refactor candidates and prepares a brief for `tech-spec`. |
| `grilling` | "grill this plan", "stress-test this design", "poke holes in this" | Interviews the user one question at a time to sharpen the plan, with a recommended answer for each question. |
| `grill-me` | "grill me" | Starts a `grilling` session. |
| `agentic-engineering` | "AI-assisted work", "model routing", "session strategy", "AI code review checklist" | Operating principles: define completion criteria, decompose into agent-sized units, route models by complexity, measure with evals. |
| `tdd-workflow` | "TDD", "write tests first", "test-driven", "RED-GREEN-REFACTOR", "fix bug", "add feature" | Test-first discipline: RED checkpoint, GREEN checkpoint, optional REFACTOR. Loads the standards topics that govern tests, seams, async behavior, and observability. |
| `coding-standards` | "coding standards", "code quality", "boundary parsing", "type contracts", "code review checklist" | Standards router that loads topic docs for modules, boundaries, errors, async workflows, testing, observability, and type contracts. |
| `verification-loop` | "verify", "quality gates", "pre-merge checks", "is this ready", "check before commit" | Four-phase quality gate: build, type-check, lint, tests with coverage. Loads the standards topics that set the verification bar, then hands off to `change-review` and `security`. |

## Usage

The skills chain into the full procedure loop:

```
1. spec or architecture-scan  → scope the work or rank refactor candidates
2. grilling / grill-me        → stress-test the plan when requirements are still fuzzy
3. tech-spec                  → typed contracts, seams, call stacks, and test slices
4. tdd-workflow +             → implementation (per unit)
   coding-standards
5. verification-loop          → build / type-check / lint / tests pass locally
6. change-review              → strict pre-merge correctness review (review plugin)
7. security                   → security gate if relevant (review plugin)
8. pr-describer               → PR body from the diff (synthesis plugin)
9. commit-message-writer      → final commit message (synthesis plugin)
```

`spec` remains the broadest entry point. Reach for `tech-spec` when an approved plan still needs typed contracts and call stacks, and `architecture-scan` when the real question is which refactor or ownership direction to pursue.

## Related plugins

- **[`investigation`](../investigation/)**: `spec`, `architecture-scan`, and `tech-spec` recommend `quick-analysis`, `deep-understanding`, and `deep-research` for investigation-shaped work.
- **[`review`](../review/)**: `verification-loop` and `tdd-workflow` hand the diff to `change-review` and `security`. `change-review` now loads `coding-standards` topics when they are present.
- **[`synthesis`](../synthesis/)**: once review passes, `pr-describer` and `commit-message-writer` complete the cycle.
- **[`meta`](../meta/)**: `agentic-engineering` recommends `prompt-optimizer` and `doc-generator` for evolving the prompts of the agents you delegate to.
- **[`build`](../build/)**: `tdd-workflow` delegates RED to `test-engineer` and GREEN or REFACTOR to `implementer`.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.

## Notes

These are skills, not droids: each encodes a procedure the main agent runs inline, applied to the current context rather than delegated. `coding-standards` is now a router, so load the relevant topic docs instead of treating the root file as the whole standard.
