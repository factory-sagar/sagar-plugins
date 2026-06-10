# review

Two pre-merge gate droids. One catches general correctness regressions, the other catches security issues. They're designed to run in parallel before you ship.

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `change-review` | Strict last-gate reviewer for diffs, commits, branches, or named files. Correctness, consent / auth gates, rollback, event reliability. | `kimi-k2.6` | `xhigh` | read-only + `Execute` |
| `security` | Evidence-based security reviewer using STRIDE + OWASP. Verifies CVEs against trusted sources (NVD, GHSA). | `gpt-5.4` | `xhigh` | read-only + `Execute` + `WebSearch` + `FetchUrl` |

## Typical flow

- Diff staged → invoke `change-review` and `security` in parallel
- Resolve findings → ship

## Why two different models

`change-review` runs on `kimi-k2.6` and `security` runs on `gpt-5.4`. Different model families with different training distributions catch different bugs. In this marketplace's testing, `kimi-k2.6` consistently caught regulatory / consent-related issues that `gpt-5.4` missed, and `gpt-5.4` consistently caught attack-path / cross-domain issues `kimi-k2.6` reasoned about less concretely. Running both in parallel gives broader coverage than running either twice.

## Output format note

`change-review` emits a label-list output (`Summary:`, `Assessment:`, `Findings:`, `Validation Notes:`) rather than the H2-heading template the prompt also describes. This is `kimi-k2.6`'s natural format ceiling, accepted after extensive prompt iteration. Substance (procedure, risk-dimension sweep, anti-patterns, hand-offs) is preserved.

## Companion plugins (recommended)

- **[`investigation`](../investigation/)** — both reviewers hand architectural questions off to `deep-understanding`.
- **[`build`](../build/)** — findings from both reviewers feed `implementer` for the fix pass; re-review the delta after.
- **[`synthesis`](../synthesis/)** — once review passes, `pr-describer` synthesizes the PR body from the same diff.

Cross-plugin hand-offs are just naming suggestions; if you haven't installed the companion plugin the hand-off is a no-op recommendation, not an error.
