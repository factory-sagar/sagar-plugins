# review

> Pre-merge gate droids plus a review-and-fix skill: strict correctness review, security review, and an end-to-end review-then-fix workflow.

Two review droids support one public workflow. `review-pr` converts short review requests
into mandatory and diff-selected policy, while explicit wording controls whether it may
report, fix locally, address comments, ship, or merge.

## Install

```bash
droid plugin install review@sagar-plugins
```

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `change-review` | Static correctness and contract review of a scoped diff. | `kimi-k3` | `max` | read-only + `Execute` |
| `security` | STRIDE/OWASP security review with verified attack paths and CVEs. | `claude-opus-4-8` | `xhigh` | read-only + web |

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `review-pr` | Review or approve a PR, branch, commit, or staged change | Selects language-agnostic mandatory and diff-driven lenses. Plain review is read-only; explicit approve, fix, comments, ship, or merge wording enables only that stronger authority. |

The public entry point is `/review-pr <target>`. Existing comment and deep-review procedures
are internal references, not competing skills.

The deep tier uses a second independent `change-review` context for broad or high-consequence
changes. The reviewing model chooses policy lenses from the changed responsibilities.

A small, well-tested edit to existing risk-sensitive logic remains light only when no
independently high-consequence responsibility applies.
Migrations, concurrency, externally controlled state, multi-phase transitions, and new or
materially rewritten authorization decisions remain deep even when small.

## Usage

1. Diff staged → hand review ownership to `review-pr`, which selects the required reviewers.
2. Resolve findings → ship.
3. Or run `/review-pr <target>`; the user's wording determines the authorized end state.

## Related plugins

- **[`investigation`](../investigation/)**: both reviewers hand architectural questions to `deep-understanding`.
- **[`build`](../build/)**: findings from both reviewers feed `implementer` for the fix pass; re-review the delta after.
- **[`synthesis`](../synthesis/)**: once review passes, `pr-describer` synthesizes the PR body from the same diff.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.

## Notes

`change-review` returns a label-list format (`Summary:`, `Assessment:`, `What This Change Does:`, `Coverage:`, `Findings:`, `Validation Notes:`, in that exact order). This is the output contract defined in the droid prompt and the format the droid produces reliably. Every finding carries a mandatory `[P<n>·<conf>]` confidence label (for example `[P1·high]`).
