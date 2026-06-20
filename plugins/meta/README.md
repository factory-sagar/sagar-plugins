# meta

> Droids and a skill for improving agentic configs: audit prompts, then apply the fixes.

Two droids for working on agentic configurations themselves. `prompt-optimizer` audits a droid or skill prompt; `doc-generator` applies the fix. Together they form an audit-and-apply loop you can run on this marketplace's own droids, on a project's `AGENTS.md` and `.factory/**`, or on any other droid set.

## Install

```bash
droid plugin install meta@sagar-plugins
```

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `prompt-optimizer` | Audit a droid or skill prompt and recommend minimal-edit improvements. Use when authoring a new droid, diagnosing poor output, or comparing prompt versions. Single-prompt or pairwise scope. | `gpt-5.4` | `xhigh` | read-only |
| `doc-generator` | Apply targeted, minimal-edit agentic-doc updates after an approved audit (from `prompt-optimizer` or `deep-understanding`) or an explicit request. The only droid in this marketplace with edit tools. | `gpt-5.4` | `xhigh` | read-only + `Execute` + `Edit` + `Create` + `ApplyPatch` |

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `audit-and-apply-loop` | "audit my prompts", "improve this droid", "fix prompt drift", "iterate on droid prompts" | Methodology for using `prompt-optimizer` and `doc-generator` together as an audit-fix-verify cycle. |

## Usage

1. Author or modify a droid or skill prompt.
2. `prompt-optimizer` audits it (with observed output if you have it).
3. `doc-generator` applies the recommended edits.
4. Re-test the droid, then iterate.

## Models

Both droids run `gpt-5.4` at `xhigh`. Prompt audits and minimal-edit application are high-stakes reasoning tasks where the deep-reasoning tier earns its cost.

## Related plugins

- **[`investigation`](../investigation/)**: pair `prompt-optimizer` (prompt-local quality) with `deep-understanding` (structural agentic-config audits), and use `doc-generator` to apply the fixes either one produces.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.

## Notes

`prompt-optimizer` is prompt-local: identity, hard constraints, anti-pattern coverage, output-template adherence, verbosity, and single-prompt or pairwise audits. For structural questions (model assignments across the set, role boundaries between droids, plugin granularity, marketplace-wide drift), use `deep-understanding` in the [`investigation`](../investigation/) plugin instead. `prompt-optimizer` flags structural issues under Hand-off and stops.
