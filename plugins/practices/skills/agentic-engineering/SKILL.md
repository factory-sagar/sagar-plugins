---
name: agentic-engineering
description: Operating principles for engineering work where AI agents perform most implementation and humans enforce quality and risk controls. Use when scoping AI-assisted work, deciding which model to route to, deciding when to start a fresh session, or framing how to review AI-generated code. Triggers on "how should I structure this AI-assisted work", "which model for X", "session strategy", "AI code review checklist".
---

# Agentic Engineering

Principles for engineering workflows where AI agents perform most of the implementation and humans (or higher-tier agents) enforce quality and risk control. This is operating-system-level guidance, not a step-by-step procedure.

## When to Activate

- Scoping a feature where AI will write most of the code.
- Deciding which model tier to use for a specific task (fast/cheap vs deep reasoning vs prose synthesis).
- Deciding when to continue the current session vs start fresh vs compact.
- Reviewing AI-generated code and you need a checklist.
- Setting up evals before starting work.

## When NOT to Activate

- The task is non-AI-assisted (human writing all the code in a vacuum).
- The task is a single-line edit that doesn't need scoping.
- The user wants execution, not principles. Just do the task.

## Operating Principles

### 1. Define completion criteria before execution

Don't start coding before you can articulate what "done" looks like. If you can't, run the `spec` skill first.

### 2. Decompose work into agent-sized units

Each unit:
- is independently verifiable (you can run it and know if it worked)
- has a single dominant risk (one thing that could break)
- has a clear done condition

The 15-minute rule: if a unit would take a focused engineer more than 15 minutes, it should probably be decomposed further.

### 3. Route model tiers by task complexity

Different models for different jobs. The sagar marketplace uses this matrix:

| Task shape | Model tier | Reason |
|---|---|---|
| Triage, classification, format-mechanical work | Fast/cheap (e.g. `glm-5`) | Output is short and constrained; speed wins |
| Implementation, refactors, complex single-file edits | Strong reasoning (e.g. `gpt-5.4`) | Needs to reason about invariants |
| Architecture, root-cause analysis, multi-file invariants | Deep reasoning (e.g. `gpt-5.4 xhigh`) | Needs to hold multiple things in working memory |
| Long-form writing, synthesis from many sources | Strongest natural prose (e.g. Claude Opus via `inherit`) | Output quality dominates token cost |
| Catching what gpt misses (regulatory, consent, subtle correctness) | Different distribution (e.g. `kimi-2.6`) | Diversity of training catches different bugs |

The principle: **delegate to the right model for the job, not "the best model" for everything**.

### 4. Measure with evals and regression checks

Define before you implement:
- A **capability eval**: "did the new behavior work?"
- A **regression eval**: "did existing behavior still work?"

Run baseline → implement → re-run → compare deltas. Without the baseline, you can't tell improvement from drift.

## Eval-First Loop

1. Define capability eval and regression eval.
2. Run baseline. Capture failure signatures.
3. Execute implementation (often delegated).
4. Re-run evals. Compare deltas.
5. If regressions appear, fix or revert.

## Session Strategy

- **Continue session** for closely-coupled units (same feature, same file area).
- **Start fresh session** after major phase transitions (e.g. spec → implementation → review). New context, fewer interference patterns.
- **Compact** after a milestone is fully complete, not during active debugging. Compaction loses recent context.

## Reviewing AI-Generated Code

When reviewing what an agent produced (or asking `change-review` to do it), prioritize:

1. **Invariants and edge cases** — does the code preserve guarantees the caller depends on?
2. **Error boundaries** — what happens when the inputs/dependencies fail?
3. **Security and auth assumptions** — is anything privileged taken on faith from untrusted input?
4. **Hidden coupling** — does this implicitly depend on something else changing?
5. **Rollout risk** — is the change reversible? Does it migrate state?

For every diff a human or AI ships, those five lenses are the gate. Hand the diff to `change-review` and `security` for the formal pass.

## Companion Skills

- `spec` — apply principle 1 (define completion criteria) to a fuzzy request.
- `tdd-workflow` — apply principle 4 (measure with evals) at the unit level.
- `verification-loop` — apply principle 4 at the build/lint/test/coverage gate.
- `coding-standards` — language-agnostic quality baseline that AI-generated code should meet.

## Companion Droids

- `quick-analysis` / `deep-understanding` — for principle 1 when you don't yet know the system.
- `change-review` / `security` — for the AI-generated-code review gate (principle 5).
- `prompt-optimizer` / `doc-generator` — for evolving the prompts of the agents you're delegating to.

## Anti-Patterns

- **One model for everything.** Wastes budget on cheap tasks; under-thinks on hard tasks. Use the matrix.
- **No baseline before implementing.** You can't tell improvement from drift without it.
- **Compacting mid-debug.** You'll lose the trail.
- **Continuing a polluted session into a new phase.** Stale context corrupts the new phase's reasoning.
- **Reviewing AI code by reading the diff line-by-line.** Use the 5 lenses + `change-review`.
- **Skipping the spec and going straight to "let the agent figure it out".** Without completion criteria, the agent can't tell done from drift either.
