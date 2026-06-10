# practices

Engineering-discipline skills. Six repeatable flows that auto-load when your task matches: PLAN → DECOMPOSE → STANDARDS → TDD → VERIFY (plus DEMO-PREP for show-time readiness). The complete loop from fuzzy idea to gate-ready change.

Skills are different from droids: a skill is a procedure the main agent runs inline (auto-loaded when its description matches your task). A droid is a sub-agent you delegate to. The skills here recommend delegating to sagar droids at the right moments.

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `spec` | "spec this out", "plan this", "decompose", "break this down", "let me think this through" | Turns a fuzzy request into a concrete spec (acceptance criteria, scope, constraints) AND decomposes it into agent-sized units, each tagged with the recommended sagar droid. The starting point for any non-trivial new work. |
| `agentic-engineering` | "AI-assisted work", "model routing", "session strategy", "AI code review checklist" | Operating principles: define completion criteria, decompose into agent-sized units, route models by complexity, measure with evals. |
| `tdd-workflow` | "TDD", "write tests first", "test-driven", "RED-GREEN-REFACTOR", "fix bug", "add feature" | Test-first discipline: RED checkpoint → GREEN checkpoint → optional REFACTOR. 80%+ coverage, three test types. |
| `coding-standards` | "coding standards", "code quality", "naming conventions", "code style", "code review checklist" | Language-agnostic baseline: KISS, DRY, YAGNI, immutability defaults, naming conventions, error handling, code-smell checklist. |
| `verification-loop` | "verify", "quality gates", "pre-merge checks", "is this ready", "check before commit" | Four-phase quality gate: build → type-check → lint → tests with coverage. Hands off to `change-review` and `security`. |
| `demo-prep` | "demo prep", "get the demo ready", "pre-demo check", "verify the demo" | Spin up a demo app, smoke-test the critical paths through the real UI, verify data/auth state, record the restart one-liner. Reads/offers a per-repo `.factory/demo-prep.md` config. |

## The full loop

```
1. spec               → spec + decomposition with droid recommendations
2. (per unit) tdd-workflow + coding-standards   → implementation
3. verification-loop  → build / type-check / lint / tests pass locally
4. change-review      → strict pre-merge correctness review (in `review` plugin)
5. security           → security gate if relevant (in `review` plugin)
6. pr-describer       → PR body from the diff (in `synthesis` plugin)
7. commit-message-writer  → final commit message (in `synthesis` plugin)
```

`spec` is the single most useful entry point — it's what you invoke when asked to start anything non-trivial.

## Companion plugins (recommended)

- **[`investigation`](../investigation/)** — `spec` recommends `quick-analysis` / `deep-understanding` / `deep-research` for investigation-shaped units.
- **[`review`](../review/)** — `verification-loop` and `tdd-workflow` hand the diff to `change-review` and `security`.
- **[`synthesis`](../synthesis/)** — once review passes, `pr-describer` and `commit-message-writer` complete the cycle.
- **[`meta`](../meta/)** — `agentic-engineering` recommends `prompt-optimizer` and `doc-generator` for evolving the prompts of the agents you delegate to.

- **[`build`](../build/)** — `tdd-workflow` delegates RED to `test-engineer` and GREEN/REFACTOR to `implementer`; `demo-prep` hands failures to `debugger`, then fixes to `implementer`.

The skills here are designed to compose with droids in the other plugins. Install all six plugins for the full experience.

## Why these are skills, not droids

Each skill encodes a procedure the main agent should run inline — TDD discipline, code-standards review, verification gates, decomposition methodology. They're guidance the main agent applies to its current context, not work to delegate to a separate sub-agent.

Droids work the other way: you hand them a scope and they return a structured result from their own context. Both have their place. The two compose: a skill auto-loads when relevant, runs through its procedure, and at the right moments recommends delegating a sub-task to a droid.
