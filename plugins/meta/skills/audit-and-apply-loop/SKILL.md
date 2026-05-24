---
name: audit-and-apply-loop
version: 1.0.0
description: |
  Methodology for evolving droid or skill prompts using `prompt-optimizer` (audit) + `doc-generator`
  (apply) as an audit-fix-verify cycle, with explicit delegation per phase and re-test verification
  before each loop iteration. The same loop produced the v2-quality prompts in this marketplace.
  Use when:
  - Authoring a new droid prompt and want a quality pass before shipping
  - Diagnosing a droid whose output keeps missing sections, hallucinating, or running forbidden commands
  - Comparing prompt v1 vs v2 to decide which to ship
  - Cleaning up drift in an existing droid set
  - Adopting droids from another marketplace into your own
  - Auditing a project's `.factory/droids/**` or `AGENTS.md` for quality and consistency
tags: [meta, prompt-engineering, methodology, droids, agentic-config, iteration]
---

# Audit-and-Apply Loop

A repeatable six-step cycle for evolving droid and skill prompts. Audit with `prompt-optimizer`, apply minimal-edit fixes with `doc-generator`, re-test against a real target, re-audit to confirm. The loop converges when no new findings appear or when remaining findings are intentionally accepted.

This skill is meta — it describes how to use the meta plugin to improve any droid or skill prompt, including the meta plugin's own droids. The same loop produced the v2-quality prompts in the sagar-plugins marketplace over multiple iterations.

## When to Activate

- Authoring a new droid prompt for the first time and you want a quality pass before shipping.
- Diagnosing a droid whose output keeps missing sections, hallucinating, running forbidden commands, or producing inconsistent format.
- Comparing v1 vs v2 of a prompt to decide which to ship.
- Cleaning up drift in an existing droid set (stale cross-references, outdated tool policies, wrong model assignments).
- Adopting droids from another marketplace into your own.
- Auditing a project's `.factory/droids/**` or `AGENTS.md` for quality and consistency.

## When NOT to Activate

- The prompt is fine and the parent task is unrelated.
- The audit target is **structural** — questions about which droid owns which role, plugin granularity decisions, model strategy across the whole set. That's `deep-understanding`'s remit (in the `investigation` plugin), not `prompt-optimizer`'s.
- Single trivial edit (fixing a typo in a description, adding a missing comma). Just edit it directly with `doc-generator` or by hand.
- The droid hasn't been invoked yet — start with running it once on a real target, then audit. Audits without observed output are inference-only and converge slowly.

## The Loop

```
┌──────────────────────────────────────────┐
│ 1. Author or modify the prompt           │
│    (write the markdown + frontmatter)    │
│    Delegate: <self> or worker            │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 2. Invoke the droid against a real       │
│    target. Capture observed output.      │
│    (Without observed output, audit       │
│     findings are inference-only.)        │
│    Delegate: the target droid itself     │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 3. prompt-optimizer audits the prompt    │
│    + observed output.                    │
│    Returns findings with severity,       │
│    confidence, and Risk-of-edit.         │
│    Delegate: prompt-optimizer droid      │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 4. Decide which findings to apply.       │
│    Skip findings with Risk-of-edit:high  │
│    unless you can re-test.               │
│    Delegate: <self>                      │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 5. doc-generator applies the chosen      │
│    findings (minimal-edit, verified).    │
│    Delegate: doc-generator droid         │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 6. Re-invoke the droid on the same       │
│    target. Compare observed output to    │
│    the audit's predictions.              │
│    Delegate: the target droid itself     │
└──────────────────┬───────────────────────┘
                   │
                   ▼
       (loop until clean OR
        until remaining findings
        are intentionally accepted)
```

## Procedure

### Step 1 — Author or modify the prompt

Use the v2-quality structure for any new droid:
- Identity (`When to Use Me` / `When NOT to Use Me`).
- Hard constraints (read-only, tool boundaries, confidence labels, findings caps).
- Phased procedure (numbered phases, not flat rules).
- Anti-patterns (concrete forbidden behaviors with examples).
- Edge cases (named scenarios with handling rules).
- Self-check (numbered pre-return verifications).
- Output template (the literal shape, with example).

**Common authoring trap: fighting a model prior.** If a model has a strong trained format (e.g., gpt models emit `Summary:` inline for code review), prompt directives won't override it. Embrace the model's natural format and constrain the substance.

**Delegation:** can be `<self>` (you write it) or `worker` (you give a self-contained spec and let worker draft). For drafts going through this loop anyway, `worker` is often fine; the loop catches issues.

### Step 2 — Invoke the droid against a real target

Do this **before** auditing. Without observed output:
- Adherence findings are `inference` only (Risk-of-edit decisions become guesswork).
- The audit can't tell which directives the model is silently ignoring.
- The audit can't tell which content surprises the model into producing junk.

**Pick a real target** that exercises the droid's typical use case. For:
- `quick-analysis` → a repo you've never triaged before
- `deep-understanding` → a repo with non-trivial architecture
- `change-review` → a real commit with non-trivial diff
- `security` → a commit touching auth or secrets
- `pr-describer` → a recent multi-file commit
- `deep-research` → a focused external question

Save the output verbatim. You'll feed it back into prompt-optimizer in Step 3.

**Delegation:** invoke the target droid itself.

### Step 3 — Run prompt-optimizer

Pass:
- The prompt file path
- The observed output from Step 2
- The audit type (`new-droid review` | `adherence diagnosis` | `version comparison` | `cross-reference sweep`)

`prompt-optimizer` returns findings with:
- **Priority** (P0–P3)
- **Confidence** (high/medium/low) — high when grounded in observed output
- **Risk-of-edit** (high/medium/low) — high when the edit may fight a model prior

It will also flag findings that require **structural** decisions (which droid owns what, model swaps, plugin granularity) under Hand-off → `deep-understanding`. Those are not for this loop.

**Delegation:** `prompt-optimizer` droid.

### Step 4 — Decide which findings to apply

Default decision rule:
- **Apply** P0/P1 with confidence high, regardless of Risk-of-edit.
- **Apply** P2/P3 with Risk-of-edit low.
- **Skip with re-test plan** P2/P3 with Risk-of-edit high, unless you have time to re-test.
- **Skip and hand-off** any finding marked as structural.

If you don't have observed output (so confidence is `low` everywhere), you have a chicken-and-egg problem. Two fixes:
- Run the droid first, then audit (preferred; the loop converges).
- Apply only the obviously-correct findings (typos, dead references, missing sections, malformed frontmatter).

**Delegation:** `<self>` — this is a judgment call, not a delegable task.

### Step 5 — doc-generator applies

Pass the chosen findings to `doc-generator`. It will:
- Read each target file in full first.
- Plan minimal edits.
- Apply via `Edit` / `Create` / `ApplyPatch`.
- Verify after each edit (rename grep, JSON parse, frontmatter shape, markdown structure).
- Skip findings labeled `Risk-of-edit: high` unless explicitly opted in.
- Skip findings that require structural decisions (hand back to `deep-understanding`).

`doc-generator` will output a report of files changed, edits applied, verifications performed, and findings skipped with reasons.

**Delegation:** `doc-generator` droid.

### Step 6 — Re-invoke and compare

Run the droid on the same target as Step 2. Compare:
- Did the audit's predicted improvements actually land in the output?
- Did anything regress?
- Are there new findings?

Three outcomes:
- **Clean:** lock the prompt and ship. Commit the audit + apply + verify cycle as a single PR.
- **New findings only (no regressions):** another loop iteration with the new findings.
- **Regressions:** revert the latest `doc-generator` pass and try a different finding subset. The applied finding fought the model harder than expected.

**Delegation:** the target droid itself.

## Delegation Map (per step)

| Step | Delegate to | Why |
|---|---|---|
| 1. Author / modify prompt | `<self>` or `worker` | Drafting; either works |
| 2. Invoke target droid | the target droid | This is the data we audit against |
| 3. Audit | `prompt-optimizer` | Specialized for prompt-local quality |
| 4. Decide which to apply | `<self>` | Judgment, not delegable |
| 5. Apply | `doc-generator` | Only droid in marketplace with edit tools |
| 6. Re-invoke and compare | the target droid + `<self>` for comparison | Re-run + manual diff of behavior |

## When to Use deep-understanding Instead

Some findings or audit-shaped questions are structural, not prompt-local. Hand off to `deep-understanding` (in `investigation` plugin) when:

- The question is "should this droid even exist" or "is this duplicating another droid".
- The question is "what's the right model assignment across the set" — that's strategy, not prompt mechanics.
- The question is "how should plugins in this marketplace be split" — granularity decision.
- The question is "is the cross-droid hand-off graph coherent" across many droids — that's structural.
- The audit's findings cluster around "the prompt is fine but the role is wrong" — re-architect, don't tweak.

`prompt-optimizer` will flag these under Hand-off and stop; the loop continues with `deep-understanding` instead.

## Companion Droids

- `prompt-optimizer` (in `meta`) — the auditor for steps 3+.
- `doc-generator` (in `meta`) — the applier for step 5.
- `deep-understanding` (in `investigation`) — for structural decisions that aren't prompt-local.
- target droid being evolved — used in steps 2 and 6.

## Anti-Patterns

- **Auditing without observed output.** All findings are `inference`; the loop can't converge cleanly. Run the droid first.
- **Applying high-Risk-of-edit findings blindly without re-test.** Those exist because the model may fight the directive; you need to verify the fight didn't backfire.
- **Letting `prompt-optimizer` make structural calls.** It's prompt-local. Structural goes to `deep-understanding`.
- **Skipping the re-test in step 6.** Without re-test, you don't know if the apply actually worked or just looked clean in the diff.
- **Flip-flopping** — applying a finding, then undoing it next loop, then re-applying. Root-cause why the finding keeps coming back before applying again.
- **Letting the prompt grow indefinitely.** Every loop iteration tends to add directives. Periodically run a "trim" pass — what can be removed without quality loss?
- **Targeting too many droids in one audit.** Pair audits work for cross-reference correctness; full-marketplace audits should hand off to `deep-understanding`.
- **Treating doc-generator's "applied" as evidence of correctness.** doc-generator verifies that edits landed syntactically (JSON parses, grep finds the new text); only step 6 verifies that the BEHAVIOR is right.
- **Bypassing doc-generator and editing prompts inline.** You lose verification (rename sweep, frontmatter check) and you risk drift between project copy and personal copy.

## Edge Cases

- **Brand-new droid, no observed output yet:** run it once on a representative target before the first audit. If you literally cannot (e.g., the droid requires elaborate setup), audit anyway with `inference` confidence and accept the loop will need extra iterations.
- **Audit finds nothing:** great, the prompt is in a good state. Lock it and move on. Skip Step 5 entirely.
- **Audit recommends a model swap:** that's a structural decision; hand off to `deep-understanding`. Do NOT let `doc-generator` change the frontmatter `model` field based on a `prompt-optimizer` finding alone.
- **Audit finds the prompt is fundamentally wrong** (wrong identity, wrong scope, wrong model class): this is full rewrite territory, not minimal-edit. Author manually (back to Step 1 with a clean slate); then loop.
- **Findings disagree across two prompts being audited together:** resolve the conflict before applying. `doc-generator` will refuse to apply contradictory edits.
- **Same finding keeps appearing every loop iteration despite being "applied":** the model is fighting the directive. Either remove the directive (give up; embrace the model's natural behavior), or rephrase entirely (try a worked example instead of a rule, or rename a section to avoid the trigger).
- **Three or more loop iterations with no convergence:** stop and root-cause. Common causes: (a) the model has a hard prior we're fighting; (b) the prompt is structurally wrong (identity/scope mismatch); (c) the target isn't exercising the right path. Hand off to `deep-understanding` for a fresh look.
- **Prompt change passes the audit but the droid produces worse output:** the audit missed something. Don't trust audit-only — Step 6 (re-test) is the final word.

## Self-Check (before declaring a prompt locked)

1. Did I run the droid against a real target (not just lint the prompt)?
2. Did I run `prompt-optimizer` with observed output, not just the prompt?
3. For each high-Risk-of-edit finding I applied, did I re-test?
4. Did I hand off structural findings to `deep-understanding`, not let `doc-generator` apply them?
5. After applying, did I re-invoke the droid and verify behavior improved?
6. Is the prompt smaller or the same size, or did it just grow? (Growth is a sign of accumulating directives without trimming.)
7. Are the changes committed with a clear message documenting which findings were applied and which were skipped?

If any answer is no, fix or document it before declaring the loop complete.
