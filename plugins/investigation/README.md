# investigation

> Droids that build understanding: fast triage, deep repo investigation, external research, and root-cause debugging.

Four droids you delegate to when you need to understand something: a repo, a subsystem, or an external question.

## Install

```bash
droid plugin install investigation@sagar-plugins
```

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `quick-analysis` | Fast triage of an unfamiliar repo: stack, structure, entry points, anomalies. Use first when you don't know the lay of the land. | `glm-5.2` | default | read-only |
| `deep-understanding` | Thorough, evidence-based investigation of a repository, subsystem, or focused question. Architecture audits and agentic-config audits. | `gpt-5.4` | `xhigh` | read-only + `Execute` |
| `deep-research` | External research using WebSearch and FetchUrl. Library evaluations, API references, comparisons, CVE follow-ups. For questions that live outside the repo. | `inherit` (Claude) | `xhigh` | read-only + `Execute` + `WebSearch` + `FetchUrl` |
| `debugger` | Root-cause a failing behavior: reproduce, rank hypotheses, prove the cause, hand a fix plan to `implementer`. Failing tests, stack traces, regressions, incident RCA. | `gpt-5.4` | `xhigh` | read-only + `Execute` |

## Usage

1. New repo or unclear scope → `quick-analysis` (60-second triage with hand-off questions).
2. Quick analysis recommends going deeper → `deep-understanding`.
3. Question lives outside the repo (library docs, CVE, best practice) → `deep-research`.
4. Something concrete is failing (test, stack trace, regression, incident) → `debugger` (root cause plus a fix plan for `implementer`).

## Models

- `glm-5.2`: fast and cheap triage.
- `gpt-5.4` (xhigh): strong architectural reasoning (`deep-understanding`) and evidence-driven root-cause work (`debugger`).
- `inherit` (Claude Opus): strongest natural prose for synthesizing external sources.

To fall back to your session default model, change `model:` to `inherit` in the droid frontmatter.

## Related plugins

- **[`review`](../review/)**: `quick-analysis` and `deep-understanding` recommend handing diffs and PRs to `change-review`, and security-shaped findings to `security`.
- **[`meta`](../meta/)**: `deep-understanding` agentic-config audits hand prompt-quality issues to `prompt-optimizer` and the fixes to `doc-generator`.
- **[`build`](../build/)**: `debugger` hands its fix plan to `implementer` and its pin-it test to `test-engineer`.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.
