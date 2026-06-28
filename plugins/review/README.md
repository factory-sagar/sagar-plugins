# review

> Pre-merge gate droids plus a review-and-fix skill: strict correctness review, security review, and an end-to-end review-then-fix workflow.

Two pre-merge gate droids and one workflow skill. One droid catches general correctness regressions, the other catches security issues; run them in parallel before you ship. The `review-fix` skill drives the full loop: review read-only, apply the fixes, verify, commit locally, and stop before push.

## Install

```bash
droid plugin install review@sagar-plugins
```

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `change-review` | Strict last-gate reviewer for diffs, commits, branches, or named files. Correctness, consent and auth gates, rollback, event reliability. | `kimi-k2.6` | `xhigh` | read-only + `Execute` |
| `security` | Evidence-based security reviewer using STRIDE and OWASP. Verifies CVEs against trusted sources (NVD, GHSA). | `gpt-5.4` | `xhigh` | read-only + `Execute` + `WebSearch` + `FetchUrl` |

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `review-fix` | "review and fix", "deep review and fix", or a PR URL / branch with intent to fix findings, not just report them | Loads the diff, picks a tier (light single-pass via `change-review`/`security`, or deep exhaustive multi-pass over a shared notes doc — auto-escalated for large/risky diffs, confirmed first), consolidates and triages findings, applies the fixes, verifies, commits locally, and asks before pushing. |

Command: `/review-fix <PR URL, branch, range, or staged>` runs the skill directly.

The deep tier ships three supporting files in the skill directory: `review-notes-format.md` (shared notes-doc and finding format), `review-worker.md` (Review subagent prompt templates), and `discover-conventions.md` (convention enumeration procedure). When the `practices` plugin is installed, deep-tier discovery is backed by `coding-standards`; otherwise it falls back to the target repo's own docs.

## Usage

1. Diff staged → invoke `change-review` and `security` in parallel.
2. Resolve findings → ship.
3. Or run `review-fix` (or `/review-fix <target>`) to review, fix, verify, and commit in one loop — it stops before push for your approval.

## Models

`change-review` runs on `kimi-k2.6` and `security` runs on `gpt-5.4`. Different model families with different training distributions catch different bugs. In this marketplace's testing, `kimi-k2.6` consistently caught regulatory and consent-related issues that `gpt-5.4` missed, while `gpt-5.4` consistently caught attack-path and cross-domain issues `kimi-k2.6` reasoned about less concretely. Running both in parallel gives broader coverage than running either twice.

## Related plugins

- **[`investigation`](../investigation/)**: both reviewers hand architectural questions to `deep-understanding`.
- **[`build`](../build/)**: findings from both reviewers feed `implementer` for the fix pass; re-review the delta after.
- **[`synthesis`](../synthesis/)**: once review passes, `pr-describer` synthesizes the PR body from the same diff.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.

## Notes

`change-review` returns a label-list format (`Summary:`, `Assessment:`, `What This Change Does:`, `Coverage:`, `Findings:`, `Validation Notes:`, in that exact order). This is the output contract defined in the droid prompt and the format `kimi-k2.6` produces reliably. Every finding carries a mandatory `[P<n>·<conf>]` confidence label (for example `[P1·high]`).
