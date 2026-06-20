# review

> Pre-merge gate droids: strict correctness review and security review.

Two pre-merge gate droids. One catches general correctness regressions, the other catches security issues. Run them in parallel before you ship.

## Install

```bash
droid plugin install review@sagar-plugins
```

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `change-review` | Strict last-gate reviewer for diffs, commits, branches, or named files. Correctness, consent and auth gates, rollback, event reliability. | `kimi-k2.6` | `xhigh` | read-only + `Execute` |
| `security` | Evidence-based security reviewer using STRIDE and OWASP. Verifies CVEs against trusted sources (NVD, GHSA). | `gpt-5.4` | `xhigh` | read-only + `Execute` + `WebSearch` + `FetchUrl` |

## Usage

1. Diff staged → invoke `change-review` and `security` in parallel.
2. Resolve findings → ship.

## Models

`change-review` runs on `kimi-k2.6` and `security` runs on `gpt-5.4`. Different model families with different training distributions catch different bugs. In this marketplace's testing, `kimi-k2.6` consistently caught regulatory and consent-related issues that `gpt-5.4` missed, while `gpt-5.4` consistently caught attack-path and cross-domain issues `kimi-k2.6` reasoned about less concretely. Running both in parallel gives broader coverage than running either twice.

## Related plugins

- **[`investigation`](../investigation/)**: both reviewers hand architectural questions to `deep-understanding`.
- **[`build`](../build/)**: findings from both reviewers feed `implementer` for the fix pass; re-review the delta after.
- **[`synthesis`](../synthesis/)**: once review passes, `pr-describer` synthesizes the PR body from the same diff.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.

## Notes

`change-review` returns a label-list format (`Summary:`, `Assessment:`, `What This Change Does:`, `Coverage:`, `Findings:`, `Validation Notes:`, in that exact order). This is the output contract defined in the droid prompt and the format `kimi-k2.6` produces reliably. Every finding carries a mandatory `[P<n>·<conf>]` confidence label (for example `[P1·high]`).
