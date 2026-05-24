# meta

Two droids for working on agentic configurations themselves. `prompt-optimizer` audits a droid or skill prompt; `doc-generator` applies the fix. They form an audit→apply loop you can run on this marketplace's own droids, on a project's `AGENTS.md` and `.factory/**`, or on any other droid set.

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `prompt-optimizer` | Audit a droid or skill prompt and recommend minimal-edit improvements. Use when authoring a new droid, diagnosing poor output, or comparing prompt versions. Single-prompt or pairwise scope. | `gpt-5.4` | `xhigh` | read-only |
| `doc-generator` | Apply targeted, minimal-edit agentic-doc updates after an approved audit (from `prompt-optimizer` or `deep-understanding`) or explicit request. The only droid in this marketplace with edit tools. | `gpt-5.4` | `xhigh` | read-only + `Execute` + `Edit` + `Create` + `ApplyPatch` |

## Typical flow

1. Author or modify a droid / skill prompt
2. `prompt-optimizer` audits it (with observed output if you have it)
3. `doc-generator` applies the recommended edits
4. Re-test the droid; iterate

## Boundary with `deep-understanding`

`prompt-optimizer` is **prompt-local**: identity, hard constraints, anti-pattern coverage, output template adherence, prompt verbosity, single-prompt or pairwise audits.

For **structural** agentic-config questions — model assignments across the set, role boundaries between droids, plugin granularity decisions, marketplace-wide drift — use `deep-understanding` (in the [`investigation`](../investigation/) plugin) instead. `prompt-optimizer` will flag structural issues under Hand-off and stop.

## Companion plugins (recommended)

- **[`investigation`](../investigation/)** — `deep-understanding` audits agentic-config structure; pair with `prompt-optimizer` for prompt-local quality and `doc-generator` to apply the fixes.

Cross-plugin hand-offs are just naming suggestions; if you haven't installed the companion plugin the hand-off is a no-op recommendation, not an error.
