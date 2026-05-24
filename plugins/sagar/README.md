# sagar

Analysis and review droid toolkit. Three sub-agents you delegate to from a parent session.

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `quick-analysis` | Fast triage of an unfamiliar repo: stack, structure, entry points. Use first when you don't know the lay of the land. | `glm-5` | default | read-only |
| `deep-understanding` | Broad, evidence-backed understanding of architecture, conventions, and agentic configuration. Use when `quick-analysis` says "go deeper". | `gpt-5.4` | `xhigh` | read-only + `Execute` |
| `change-review` | Strict reviewer for diffs, commits, or explicitly scoped files. Use before merging or after staging changes. | `gpt-5.4` | `high` | read-only + `Execute` |

## Typical flow

1. New repo or unclear scope → `quick-analysis`
2. Quick analysis recommends going deeper → `deep-understanding`
3. Have a diff to ship → `change-review`

## Models

Models are pinned (`gpt-5.4`, `glm-5`). If you don't have access to one, change the `model:` field in the droid's frontmatter to `inherit`.
