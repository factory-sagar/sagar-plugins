# sagar

Multi-model droid toolkit. Nine specialized sub-agents for investigation, review, research, synthesis, and meta-prompt audits. Designed for delegation: each droid has a fixed role, a phased procedure, anti-patterns, edge cases, and a hand-off contract to other droids in the set.

## Droids

### Investigation

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `quick-analysis` | Fast triage of an unfamiliar repo: stack, structure, entry points, anomalies, and which droid to delegate to next. | `glm-5` | default | read-only |
| `deep-understanding` | Thorough, evidence-based investigation of a repository, subsystem, or focused question. Architecture audits and agentic-config audits. | `gpt-5.4` | `xhigh` | read-only + `Execute` |
| `deep-research` | External research using WebSearch + FetchUrl. Library evaluations, API references, comparisons, CVE follow-ups. Distinct from `deep-understanding` — this is for questions that live OUTSIDE the repo. | `inherit` (Claude) | `xhigh` | read-only + `WebSearch` + `FetchUrl` |

### Review

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `change-review` | Strict last-gate reviewer for diffs, commits, branches, or named files. General correctness, consent / auth, rollback, event reliability. | `kimi-2.6` | `xhigh` | read-only + `Execute` |
| `security` | Evidence-based security reviewer using STRIDE + OWASP. Verifies CVEs against trusted sources. Pairs with `change-review`. | `gpt-5.4` | `xhigh` | read-only + `Execute` + `WebSearch` + `FetchUrl` |

### Synthesis

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `pr-describer` | Write a PR title and body from a diff. Structured what / why / testing / breaking changes / follow-ups. | `inherit` (Claude) | `high` | read-only + `Execute` |
| `commit-message-writer` | Write a Conventional Commits message from staged or specified changes. Fast and format-mechanical. | `glm-5` | default | read-only + `Execute` |

### Meta

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `prompt-optimizer` | Audit a droid or skill prompt and recommend minimal-edit improvements. Use when authoring a new droid or diagnosing poor output. | `gpt-5.4` | `xhigh` | read-only |
| `doc-generator` | Apply targeted, minimal-edit agentic-doc updates after an approved audit (from `prompt-optimizer` or `deep-understanding`) or explicit request. | `gpt-5.4` | `xhigh` | read-only + `Edit` + `Create` + `ApplyPatch` |

## Composition patterns

The droids compose. Common chains:

- **New repo → understand → ship**: `quick-analysis` → `deep-understanding` → (you implement) → `change-review` → `pr-describer`
- **External-question pipeline**: `deep-research` → (you decide) → implement → `commit-message-writer`
- **Audit-and-apply for the agentic config itself**: `deep-understanding` (audit `.factory/**`) → `doc-generator` (apply)
- **Prompt iteration**: write a droid → `prompt-optimizer` (audit) → `doc-generator` (apply) → re-test
- **Pre-merge gate**: `change-review` + `security` in parallel → resolve findings → `pr-describer`

## Why multiple models

Different model families catch different things:

- **`glm-5`** — fast and cheap; perfect for triage and format-mechanical work (`quick-analysis`, `commit-message-writer`).
- **`gpt-5.4 xhigh`** — strong architectural reasoning; best for investigations and audits (`deep-understanding`, `security`, `prompt-optimizer`, `doc-generator`).
- **`kimi-2.6 xhigh`** — different training distribution from gpt; consistently catches regulatory / consent / subtle correctness issues that gpt misses (`change-review`).
- **`inherit` (Claude Opus)** — strongest natural prose; best for prose synthesis and external research (`pr-describer`, `deep-research`).

This is the whole point of the marketplace: **delegate to the right model for the job, not "the best model" for everything**.

## Output format note

`change-review` emits a label-list output (`Summary:`, `Assessment:`, `Findings:`, `Validation Notes:`) rather than the H2-heading template the prompt also describes. This is `kimi-2.6`'s natural format ceiling, accepted after extensive prompt iteration. Substance (procedure, risk dimensions, anti-patterns, hand-offs) is preserved.

## Customizing models

Models are pinned. If you don't have access to a model, change the `model:` field in the droid's frontmatter to `inherit` to fall back to your session's default.

## Tool surface

Several droids expose `WebSearch` / `FetchUrl` / `Edit` / `Create` / `ApplyPatch`. Each droid's prompt explicitly constrains how those tools may be used (e.g., `security` may only WebSearch trusted CVE sources; `doc-generator` may only Edit agentic-config files). Read the droid's `Hard Constraints` section before installing in environments with sensitive policies.
