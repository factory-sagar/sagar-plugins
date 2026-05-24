---
name: agentic-engineering
description: Operating principles for engineering work where AI agents perform most implementation and humans (or higher-tier agents) enforce quality and risk control. Defines completion criteria, decomposition rules, model-routing matrix, session strategy, eval-first loop, and a 5-lens checklist for reviewing AI-generated code — each with explicit recommendations for which droid or worker to delegate to. Use when scoping AI-assisted work, deciding which model for what, structuring sessions for delegation, reviewing AI-generated code, or framing how to orchestrate multi-step agent chains. Auto-activates on "AI-assisted work", "how to structure this", "which model for X", "session strategy", "AI code review", "delegate this", "orchestrate", "agent chain", "model routing".
---

# Agentic Engineering

Operating-system-level principles for engineering work where AI agents do most of the implementation and you (or specialized review droids) enforce quality and risk control. This is **how to think about delegation**, not a step-by-step procedure. Read once; refer back when scoping multi-step work.

The thesis: **delegate to the right model for the job**, not "the best model" for everything. Different model families have different strengths and different costs; bundling everything onto one tier wastes budget on cheap tasks and under-thinks on hard ones. The sagar-plugins marketplace is built around this thesis.

## When to Activate

- Scoping a feature where AI will write most of the code.
- Deciding which model tier to use for a specific subtask.
- Deciding when to continue the current session vs start fresh vs compact.
- Reviewing AI-generated code and you need a structured checklist.
- Setting up evals before starting work.
- Designing a multi-step agent chain (delegating across multiple droids/workers).
- Onboarding a teammate to the marketplace's delegation model.

## When NOT to Activate

- The task is non-AI-assisted (human writing all the code in a vacuum).
- The task is a single-line edit that doesn't need scoping.
- The user wants execution, not principles. **Just do the task** — these principles apply implicitly, you don't need to recite them.

## The Five Operating Principles

### Principle 1 — Define completion criteria before execution

You can't tell "done" from "drift" without an explicit definition. If you can't articulate what done looks like in 1–2 sentences plus a list of testable acceptance criteria, you don't have a spec; you have a vibe.

**Apply this:** run the `spec` skill first when scope is fuzzy. `spec` produces both the definition of done and a decomposition with droid recommendations per unit.

### Principle 2 — Decompose work into agent-sized units

Each unit:
- **Independently verifiable**: you can run it and tell if it worked.
- **Single dominant risk**: one thing that could break, not three.
- **Clear done condition**: an observable signal, not a feeling.

The **15-minute rule**: if a unit would take a focused engineer more than 15 minutes of actual implementation time (excluding investigation), decompose it further.

**Apply this:** `spec` does the decomposition. For each unit, the recommended delegate is in the spec's Decomposition table.

### Principle 3 — Route model tiers by task complexity

Different models for different jobs. The sagar marketplace uses this matrix:

| Task shape | Model tier | Example droid | Reason |
|---|---|---|---|
| Triage, classification, format-mechanical work | Fast / cheap (e.g. `glm-5`) | `quick-analysis`, `commit-message-writer` | Output is short and constrained; speed wins |
| Implementation, refactors, focused single-file edits | Strong reasoning (e.g. `gpt-5.4`) | (worker with reasoning-capable model) | Needs to reason about invariants without blowing budget |
| Architecture, root-cause, multi-file invariants, deep audits | Deep reasoning (e.g. `gpt-5.4 xhigh`) | `deep-understanding`, `security`, `prompt-optimizer`, `doc-generator` | Needs to hold multiple things in working memory |
| Long-form prose synthesis, external research | Strongest natural prose (e.g. Claude Opus via `inherit`) | `pr-describer`, `deep-research` | Output quality dominates token cost |
| Catching what gpt misses (regulatory, consent, subtle correctness) | Different training distribution (e.g. `kimi-2.6`) | `change-review` | Distributional diversity catches different bugs |

**Apply this:** when picking a delegate in a `spec` decomposition or when orchestrating ad-hoc, consult this matrix. Don't default to "the best model" — default to the right tier.

### Principle 4 — Measure with evals and regression checks

Before implementing, define:
- A **capability eval**: "did the new behavior work?"
- A **regression eval**: "did existing behavior still work?"

Run baseline → implement → re-run → compare deltas.

Without the baseline, you can't tell improvement from drift, or fix-the-bug from break-something-else.

**Apply this:** for code, the capability eval is the new test(s) added by `tdd-workflow`; the regression eval is the existing test suite run by `verification-loop`. For non-code (prompt iteration, model swaps), define a small target dataset and a comparison function before swapping anything.

### Principle 5 — Review AI-generated code through five fixed lenses

When reviewing what an agent (or worker) produced — whether you review inline or delegate to `change-review` — prioritize these five lenses, in order:

1. **Invariants and edge cases** — does the code preserve guarantees the caller depends on? What happens at boundaries (empty, max, null, concurrent)?
2. **Error boundaries** — what happens when inputs or dependencies fail? Are errors caught at the right granularity?
3. **Security and auth assumptions** — is anything privileged taken on faith from untrusted input? Are auth checks present where needed?
4. **Hidden coupling** — does this implicitly depend on something else changing? Will it silently break if a related file is updated independently?
5. **Rollout risk** — is the change reversible? Does it migrate state? Are old clients still supported?

**Apply this:** for every diff a human or AI ships, hand it to `change-review` (droid) for the formal pass on lenses 1, 2, 4, 5; hand to `security` for lens 3 if anything in the diff touches auth/secrets/consent/untrusted input.

## The Eval-First Loop

A loop that operationalizes principles 1 and 4.

```
1. Define capability eval (the new behavior must pass these).
   Define regression eval (existing behavior must still pass).
2. Run baseline. Capture failure signatures.
   - If the capability eval is failing, that's expected (the behavior doesn't exist yet).
   - If the regression eval is failing, fix it before continuing — you can't measure deltas on an unstable baseline.
3. Execute implementation (often delegated to worker via tdd-workflow).
4. Re-run both evals.
5. Compare deltas:
   - Capability eval improved? → ✓ progress
   - Regression eval still passes? → ✓ no breakage
   - Either regressed? → ✗ stop and fix or revert
6. If both green and capability fully passes → unit done.
   Hand off to verification-loop → change-review → security → pr-describer.
```

## Session Strategy

How to manage context across a multi-step delegation.

- **Continue the current session** for closely-coupled units (same feature, same file area, same model tier). Context reuse helps.
- **Start a fresh session** after major phase transitions (e.g., spec → implementation → review). New context, fewer interference patterns from prior reasoning.
- **Compact** after a milestone is fully complete, not during active debugging. Compaction loses recent context; debug needs that context.
- **Delegate to a fresh worker** rather than continue inline when:
  - The subtask requires reading a lot of code (would balloon main context).
  - The subtask is mechanical (worker is cheaper than running it inline at the main agent's model tier).
  - The output of the subtask is summarizable (worker returns a 10-line summary instead of the main agent doing it and consuming 1000 lines of tool output).

## Multi-Step Agent Chains

For a typical "spec to merge" workflow:

```
spec (skill, inline)
  ├── quick-analysis (droid)        — for "what's the system look like"
  ├── deep-understanding (droid)    — for "how does this subsystem work"
  └── deep-research (droid)         — for "what's the right library/CVE/pattern"
  ↓
spec output: decomposition with droid recommendations
  ↓
for each unit:
  tdd-workflow (skill, orchestrates worker delegations for RED + GREEN + REFACTOR)
  OR
  worker (direct delegation, no TDD needed)
  ↓
verification-loop (skill, may delegate phases to worker)
  ↓
change-review (droid)  +  security (droid, if applicable)  [parallel]
  ↓
resolve findings; may loop back to worker for fixes
  ↓
pr-describer (droid) — synthesizes PR body from the diff + reviewer hand-offs
  ↓
commit-message-writer (droid) — final squash message
```

For the meta loop (iterating on droid prompts themselves):

```
authored or modified prompt
  ↓
invoke the droid against a real target — capture observed output
  ↓
prompt-optimizer (droid) — audits prompt + observed output, returns findings with risk-of-edit
  ↓
doc-generator (droid) — applies the chosen findings (minimal-edit, verified)
  ↓
re-invoke and compare → either lock or loop
```

The `audit-and-apply-loop` skill (in the `meta` plugin) documents this loop in full.

## Delegation Map (where to delegate by purpose)

| Purpose | Delegate to | Plugin |
|---|---|---|
| Repo triage / shape understanding | `quick-analysis` | investigation |
| Deep system / architecture / agentic-config understanding | `deep-understanding` | investigation |
| External research with sources and dates | `deep-research` | investigation |
| Strict pre-merge correctness review | `change-review` | review |
| Security review (STRIDE + OWASP + CVE) | `security` | review |
| PR body synthesis | `pr-describer` | synthesis |
| Conventional Commits message | `commit-message-writer` | synthesis |
| Audit a droid/skill prompt | `prompt-optimizer` | meta |
| Apply audit findings to agentic-config | `doc-generator` | meta |
| Implement code that doesn't fit a specialized droid | `worker` (Factory built-in) | — |
| Procedural step the main agent runs (asking user, drafting prose for context, picking a delegate) | `<self>` | — |

## Companion Skills

- `spec` — applies principle 1 (define completion criteria) and principle 2 (decompose into agent-sized units) to a fuzzy request.
- `tdd-workflow` — applies principle 4 (measure with evals) at the unit level, with explicit worker delegation for RED/GREEN/REFACTOR.
- `verification-loop` — applies principle 4 at the build/lint/test/coverage gate.
- `coding-standards` — the rubric for principle 5 lens 1 (invariants and edge cases) and lens 5 (rollout risk).
- `audit-and-apply-loop` (in `meta` plugin) — applies these principles to droid-prompt iteration itself.

## Anti-Patterns

- **One model for everything.** Wastes budget on triage and under-thinks on architecture. Use the matrix.
- **No baseline before implementing.** You can't tell improvement from drift without it.
- **Compacting mid-debug.** You'll lose the failure trail. Compact at milestone boundaries only.
- **Continuing a polluted session into a new phase.** Stale context corrupts the new phase's reasoning. Start fresh between phases.
- **Reviewing AI code by reading the diff line-by-line yourself.** Use the 5 lenses + delegate to `change-review`. Line-by-line review by the main agent burns context.
- **Skipping the spec and going straight to "let the agent figure it out".** Without completion criteria, the agent can't tell done from drift either.
- **Delegating to worker without a self-contained prompt.** Worker starts fresh. If your prompt assumes context the worker doesn't have, you get garbage.
- **Inventing a droid name that doesn't exist.** Stay in the Delegation Map. If no droid fits, use `worker`.
- **Treating "the best model" as a fixed answer.** It depends on the task. Use the matrix.
- **Treating evals as nice-to-have.** Without evals, every commit is an unmeasured change. Set them up before the work, not after.

## Edge Cases

- **Task is too small to need delegation** (one-line change, typo fix): just do it inline. Principles apply implicitly.
- **Task is so research-heavy the implementation is trivial in comparison**: front-load `deep-research` + `deep-understanding`, then a tiny implementation unit at the end.
- **Task requires capabilities no droid in the marketplace covers** (e.g., custom domain-specific workflow): delegate to `worker` with a thorough self-contained prompt. Consider whether the gap suggests a new droid (then `spec` it out as its own project).
- **Multiple model tiers needed sequentially in one unit** (e.g., fast model summarizes, deep model reasons over the summary): chain explicitly — first worker call with fast model, output passed as input to second worker call with deep model.
- **No specialized droid in the marketplace fits, but the task is delegation-shaped**: write a one-shot worker prompt with the explicit principles applied (criteria, decomposition, lenses).
- **Eval is hard to define for a subjective task** (e.g., "make the prose better"): use a comparison-based eval ("is this better than the baseline?") instead of an absolute one. Or accept that the unit is subjective and ship without an eval, but flag it.
- **Session is approaching context limit mid-task**: stop, compact at the natural boundary if possible, or fresh-start with a handoff doc that captures the current state and next steps. Don't try to push through.
