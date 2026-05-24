# sagar

Analysis and review droid toolkit. Three sub-agents you delegate to from a parent session.

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `quick-analysis` | Fast triage of an unfamiliar repo: stack, structure, entry points, anomalies. Use first when you don't know the lay of the land. | `glm-5` | default | read-only |
| `deep-understanding` | Thorough, evidence-backed investigation of a repository, subsystem, or focused question. Use when `quick-analysis` says "go deeper", or for architecture / agentic-configuration audits. | `gpt-5.4` | `xhigh` | read-only + `Execute` |
| `change-review` | Strict last-gate reviewer for diffs, commits, branches, or named files. Finds correctness, consent / auth, rollback, and event-reliability risks before merge. | `kimi-2.6` | `xhigh` | read-only + `Execute` |

## Typical flow

1. New repo or unclear scope → `quick-analysis` (60-second triage with hand-off questions)
2. `quick-analysis` recommends going deeper → `deep-understanding`
3. Have a diff to ship → `change-review`

The droids are designed to compose: each one's output is shaped to seed the next, and each labels its findings with confidence.

## Why three different models

Different model families catch different bugs:

- **`glm-5`** is fast and cheap — perfect for the under-60-second triage.
- **`gpt-5.4 xhigh`** has strong architectural reasoning — best for deep investigations.
- **`kimi-2.6 xhigh`** has a different training distribution from the gpt family — it has consistently caught regulatory and consent-related issues that gpt models miss.

## Output format notes

`change-review` emits a label-list format (`Summary:`, `Assessment:`, `Findings:`, `Validation Notes:`) rather than the full eight-section template the prompt suggests. This is a model-trained-output ceiling that we accepted after extensive prompt iteration. The investigation procedure (risk dimension sweep, scope discipline, hand-off concept) all run as designed; only the final output template is shorter than the other two droids.

## Customizing models

Models are pinned. If you don't have access to one, change the `model:` field in the droid's frontmatter to `inherit` to fall back to your session's default model.
