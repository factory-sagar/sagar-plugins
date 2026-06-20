# practices

> Engineering-discipline skills: plan, decompose, set standards, test, and verify.

Five repeatable flows that auto-load when your task matches: PLAN, DECOMPOSE, STANDARDS, TDD, VERIFY. Together they cover the loop from a fuzzy idea to a gate-ready change.

Skills differ from droids: a skill is a procedure the main agent runs inline (auto-loaded when its description matches your task), while a droid is a sub-agent you delegate to. The skills here recommend delegating to sagar droids at the right moments.

## Install

```bash
droid plugin install practices@sagar-plugins
```

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `spec` | "spec this out", "plan this", "decompose", "break this down", "let me think this through" | Turns a fuzzy request into a concrete spec (acceptance criteria, scope, constraints) and decomposes it into agent-sized units, each tagged with the recommended sagar droid. The starting point for any non-trivial new work. |
| `agentic-engineering` | "AI-assisted work", "model routing", "session strategy", "AI code review checklist" | Operating principles: define completion criteria, decompose into agent-sized units, route models by complexity, measure with evals. |
| `tdd-workflow` | "TDD", "write tests first", "test-driven", "RED-GREEN-REFACTOR", "fix bug", "add feature" | Test-first discipline: RED checkpoint, GREEN checkpoint, optional REFACTOR. 80%+ coverage across three test types. |
| `coding-standards` | "coding standards", "code quality", "naming conventions", "code style", "code review checklist" | Language-agnostic baseline: KISS, DRY, YAGNI, immutability defaults, naming conventions, error handling, code-smell checklist. |
| `verification-loop` | "verify", "quality gates", "pre-merge checks", "is this ready", "check before commit" | Four-phase quality gate: build, type-check, lint, tests with coverage. Hands off to `change-review` and `security`. |

## Usage

The skills chain into the full procedure loop:

```
1. spec                   → spec + decomposition with droid recommendations
2. tdd-workflow +         → implementation (per unit)
   coding-standards
3. verification-loop      → build / type-check / lint / tests pass locally
4. change-review          → strict pre-merge correctness review (review plugin)
5. security               → security gate if relevant (review plugin)
6. pr-describer           → PR body from the diff (synthesis plugin)
7. commit-message-writer  → final commit message (synthesis plugin)
```

`spec` is the single most useful entry point: invoke it when asked to start anything non-trivial.

## Related plugins

- **[`investigation`](../investigation/)**: `spec` recommends `quick-analysis`, `deep-understanding`, and `deep-research` for investigation-shaped units.
- **[`review`](../review/)**: `verification-loop` and `tdd-workflow` hand the diff to `change-review` and `security`.
- **[`synthesis`](../synthesis/)**: once review passes, `pr-describer` and `commit-message-writer` complete the cycle.
- **[`meta`](../meta/)**: `agentic-engineering` recommends `prompt-optimizer` and `doc-generator` for evolving the prompts of the agents you delegate to.
- **[`build`](../build/)**: `tdd-workflow` delegates RED to `test-engineer` and GREEN/REFACTOR to `implementer`.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.

## Notes

These are skills, not droids: each encodes a procedure the main agent runs inline (TDD discipline, code-standards review, verification gates, decomposition methodology), applied to the current context rather than delegated. A skill auto-loads when relevant, runs its procedure, and at the right moments recommends delegating a sub-task to a droid.
