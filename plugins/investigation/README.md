# investigation

Three droids you delegate to when you need to understand something — a repo, a subsystem, or an external question.

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `quick-analysis` | Fast triage of an unfamiliar repo: stack, structure, entry points, anomalies. Use first when you don't know the lay of the land. | `glm-5.1` | default | read-only |
| `deep-understanding` | Thorough, evidence-based investigation of a repository, subsystem, or focused question. Architecture audits and agentic-config audits. | `gpt-5.4` | `xhigh` | read-only + `Execute` |
| `deep-research` | External research using WebSearch + FetchUrl. Library evaluations, API references, comparisons, CVE follow-ups. For questions that live OUTSIDE the repo. | `inherit` (Claude) | `xhigh` | read-only + `Execute` + `WebSearch` + `FetchUrl` |

## Typical flow

1. New repo or unclear scope → `quick-analysis` (60-second triage with hand-off questions)
2. Quick analysis recommends going deeper → `deep-understanding`
3. Question lives outside the repo (library docs, CVE, best practice) → `deep-research`

## Companion plugins (recommended)

This plugin pairs with:

- **[`review`](../review/)** — `quick-analysis` and `deep-understanding` recommend handing diffs/PRs to `change-review` and security-shaped findings to `security`.
- **[`meta`](../meta/)** — `deep-understanding` agentic-config audits hand off prompt-quality issues to `prompt-optimizer` and apply-the-fixes to `doc-generator`.

Cross-plugin hand-offs are just naming suggestions; if you haven't installed the companion plugin the hand-off is a no-op recommendation, not an error.

## Models pinned per droid

- `glm-5.1` — fast/cheap triage
- `gpt-5.4 xhigh` — strong architectural reasoning
- `inherit` (Claude Opus) — strongest natural prose for synthesizing external sources

To fall back to your session default model, change `model:` to `inherit` in the droid frontmatter.
