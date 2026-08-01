# meta

> A droid and a skill for improving agentic configs: audit prompts in-session, then apply the fixes.

One droid and one skill for working on agentic configurations themselves. The `audit-and-apply-loop` skill runs the audit-fix-verify cycle; `doc-generator` applies the approved edits. You can run the loop on this marketplace's own droids, on a project's `AGENTS.md` and `.factory/**`, or on any other droid set.

## Install

```bash
droid plugin install meta@sagar-plugins
```

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `doc-generator` | Apply approved, minimal agentic-config edits. | `gpt-5.6-terra` | `high` | read/write + verification |

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `audit-and-apply-loop` | "audit my prompts", "improve this droid", "fix prompt drift", "iterate on droid prompts" | In-session prompt audit against observed behavior, then `doc-generator` applies, then re-test. |

## Usage

1. Author or modify a droid or skill prompt.
2. Audit it in-session against observed output (the `audit-and-apply-loop` lens).
3. `doc-generator` applies the recommended edits.
4. Re-test the droid, then iterate.

## Models

`doc-generator` uses `gpt-5.6-terra` for precise, minimal application.

## Related plugins

- **[`investigation`](../investigation/)**: `deep-understanding` owns structural agentic-config audits (role boundaries, model strategy, plugin granularity); use `doc-generator` to apply the fixes either pass produces.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.

## Notes

The in-session audit is prompt-local: identity, hard constraints, anti-pattern coverage, output-template adherence, verbosity, and single-prompt or pairwise audits. For structural questions (model assignments across the set, role boundaries between droids, plugin granularity, marketplace-wide drift), use `deep-understanding` in the [`investigation`](../investigation/) plugin instead.
