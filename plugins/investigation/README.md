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
| `quick-analysis` | Fast triage of an unfamiliar repo: stack, structure, entry points, anomalies. | `gpt-5.6-luna` | `high` | read-only |
| `deep-understanding` | Evidence-based repository, subsystem, architecture, and agentic-config investigation. | `gpt-5.6-sol` | `xhigh` | read-only + `Execute` |
| `deep-research` | External research using WebSearch and FetchUrl. Library evaluations, API references, comparisons, CVE follow-ups. For questions that live outside the repo. | `claude-opus-4-8` | `xhigh` | read-only + `Execute` + `WebSearch` + `FetchUrl` |
| `debugger` | Reproduce and root-cause failing behavior before implementation. | `gpt-5.6-sol` | `xhigh` | read-only + `Execute` |

## Usage

1. New repo or unclear scope → `quick-analysis` (60-second triage with hand-off questions).
2. Quick analysis recommends going deeper → `deep-understanding`.
3. Question lives outside the repo (library docs, CVE, best practice) → `deep-research`.
4. Something concrete is failing (test, stack trace, regression, incident) → `debugger` (root cause plus a fix plan for `implementer`).

## Models

- `gpt-5.6-luna`: low-cost triage.
- `gpt-5.6-sol` (xhigh): architecture and root-cause work.
- `claude-opus-4-8` (xhigh): strongest natural prose for synthesizing external sources.

Models are pinned by policy — no droid uses `inherit`, so its output distribution never depends on the parent session's model (and `reasoningEffort` is ignored under `inherit`). `scripts/validate.mjs` enforces this.

## Related plugins

- **[`review`](../review/)**: `quick-analysis` and `deep-understanding` recommend handing diffs and PRs to `change-review`, and security-shaped findings to `security`.
- **[`meta`](../meta/)**: `deep-understanding` agentic-config audits hand prompt-quality issues to `prompt-optimizer` and the fixes to `doc-generator`.
- **[`build`](../build/)**: `debugger` hands its fix plan to `implementer` and its pin-it test to `test-engineer`.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.
