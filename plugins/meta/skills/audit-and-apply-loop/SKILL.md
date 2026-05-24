---
name: audit-and-apply-loop
description: Methodology for using prompt-optimizer and doc-generator together as an audit-fix-verify cycle on droid or skill prompts. Use when authoring, evolving, or maintaining agentic configuration. Triggers on "audit my prompts", "improve this droid", "fix prompt drift", "iterate on droid prompts".
---

# Audit-and-Apply Loop

A repeatable cycle for evolving droid and skill prompts: audit with `prompt-optimizer`, apply fixes with `doc-generator`, re-test against a real target, re-audit to confirm.

This skill is meta — it describes how to use the meta plugin. Read it once when starting prompt work; refer back when results look weak.

## When to Activate

- Authoring a new droid prompt for the first time.
- Diagnosing a droid whose output keeps missing sections, hallucinating, or running forbidden commands.
- Comparing v1 vs v2 of a prompt to decide which to ship.
- Cleaning up drift in an existing droid set (stale cross-references, outdated tool policies, wrong model assignments).
- Adopting droids from another marketplace into your own.

## When NOT to Activate

- The prompt is fine and the parent task is unrelated.
- The audit target is **structural** (which droid owns what role, plugin granularity, model strategy across the set). That's `deep-understanding`'s remit, not `prompt-optimizer`'s.
- Single tiny edit (e.g. fixing a typo in a description). Just edit it directly.

## The Loop

```
┌──────────────────────────────────────────┐
│ 1. Author or modify the prompt           │
│    (write the markdown + frontmatter)    │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 2. Invoke the droid against a real       │
│    target. Capture observed output.      │
│    (Without observed output, audit       │
│     findings are inference-only.)        │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 3. prompt-optimizer audits the prompt    │
│    + observed output.                    │
│    Returns findings with severity,       │
│    confidence, and Risk-of-edit.         │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 4. Decide which findings to apply.       │
│    Skip findings tagged Risk-of-edit:    │
│    high unless you can re-test.          │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 5. doc-generator applies the chosen      │
│    findings (minimal-edit, verified).    │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ 6. Re-invoke the droid on the same       │
│    target. Compare observed output to    │
│    the audit's predictions.              │
└──────────────────┬───────────────────────┘
                   │
                   ▼
            (loop until clean)
```

## Procedure

### Step 1 — Author or modify the prompt

Use the v2 quality structure for any new droid:
- Identity (when to use, when not to use)
- Hard constraints (read-only, tool boundaries, confidence labels, findings caps)
- Phased procedure (numbered phases, not flat rules)
- Anti-patterns (concrete forbidden behaviors with examples)
- Edge cases (named scenarios with handling rules)
- Self-check (numbered pre-return verifications)
- Output template (the literal shape, with example)

Common authoring trap: **fighting a model prior**. If a model has a strong trained format (e.g. gpt models emit `Summary:` inline for code review), prompt directives won't override it. Embrace the model's natural format and constrain the substance.

### Step 2 — Invoke the droid against a real target

Do this before auditing. Without observed output:
- Adherence findings are `inference` only.
- The audit can't tell which directives the model is silently ignoring.
- The audit can't tell which content surprised a model into producing junk.

Pick a real target that exercises the droid's typical use case. Save the output verbatim.

### Step 3 — Run prompt-optimizer

Pass the prompt file + the observed output. Specify whether this is a new-droid review, adherence diagnosis, version comparison, or cross-reference sweep.

prompt-optimizer returns findings with:
- **Priority** (P0–P3)
- **Confidence** (high/medium/low)
- **Risk-of-edit** (high/medium/low)

### Step 4 — Decide which to apply

Default rule: apply P0/P1 with confidence high, regardless of Risk-of-edit. Apply P2/P3 if Risk-of-edit is low. Skip P2/P3 with high Risk-of-edit unless you can re-test.

If you don't have observed output (so confidence is `low` everywhere), you have a chicken-and-egg problem. Two fixes:
- Run the droid first, then audit (preferred).
- Apply only the obviously-correct findings (typos, dead references, missing sections).

### Step 5 — doc-generator applies

Pass the chosen findings to `doc-generator`. It will:
- Read each target file in full first.
- Plan minimal edits.
- Apply.
- Verify (rename grep, JSON parse, frontmatter shape).
- Skip findings labeled `Risk-of-edit: high` unless explicitly opted in.
- Skip findings that require structural decisions (those go back to `deep-understanding`).

### Step 6 — Re-invoke and compare

Run the droid on the same target. Compare:
- Did the audit's predicted improvements actually land?
- Did anything regress?
- Are there new findings?

If clean: lock the prompt and ship. If new findings: another loop iteration. If regressions: revert the latest doc-generator pass and try a different finding subset.

## Companion Droids

- `prompt-optimizer` (in `meta`) — the auditor.
- `doc-generator` (in `meta`) — the applier.
- `deep-understanding` (in `investigation`) — for structural decisions that aren't prompt-local.

## Anti-Patterns

- **Auditing without observed output.** All findings are `inference`; the loop can't converge.
- **Applying high-Risk-of-edit findings blindly.** Those exist because the model may fight the directive.
- **Letting prompt-optimizer make structural calls.** It's prompt-local; structural calls go to `deep-understanding`.
- **Skipping the re-test step.** Without re-test, you don't know if the apply actually worked or just looked clean.
- **Flip-flopping.** If a finding got applied last loop and is now being undone this loop, root-cause why before applying again.
- **Letting the prompt grow indefinitely.** Every loop iteration tends to add directives. Periodically run a "trim" pass — what can be removed without quality loss?
- **Targeting too many droids in one audit.** Pair-audits work for cross-reference; full-marketplace audits hand off to `deep-understanding`.

## Edge Cases

- **Brand-new droid, no observed output yet:** run it once on a representative target before the first audit. If you can't (e.g. it requires elaborate setup), audit anyway with `inference` confidence and accept the loop will need extra iterations.
- **Audit finds nothing:** great, the prompt is in a good state. Lock it and move on.
- **Audit recommends a model swap:** that's a structural decision; hand off to `deep-understanding` rather than letting `doc-generator` change the frontmatter.
- **Audit finds the prompt is fundamentally wrong** (wrong identity, wrong scope, wrong model class): full rewrite, not a minimal-edit pass. Author manually; then loop.
- **Findings disagree across two prompts being audited together:** resolve the conflict before applying. `doc-generator` will refuse to apply contradictory edits.
