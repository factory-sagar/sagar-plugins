# Golden Task Eval Pack

This pack gives prompt changes a repeatable regression check before they ship. Run each task against the relevant skill or droid, then score the output against the rubric in the task file.

Run a task headlessly with `scripts/run-golden-task.sh <task-file> [--judge]`: it extracts the task's optional ` ```bash ` Setup block into a scratch git repo, runs the ` ```text ` Prompt via `droid exec`, saves the transcript under `evals/runs/`, and with `--judge` scores it against [`JUDGE.md`](./JUDGE.md). Accepted transcripts live in [`../baselines/`](../baselines/) and are diffed on later runs.

Droid-targeted tasks run inline on the exec session model because `droid exec` has no Task tool — the runner therefore measures contract adherence for droid tasks, not the pinned model. Model A/Bs for droids run in-session via the Task tool with a temporary `.factory/droids/` variant (see the root README "Fable-class models").

## Pass rule

- All critical tasks must pass.
- No output may violate a must-not-do rule.
- Overall score must be at least 85%.

## Tasks

| Task | Target | Critical |
| --- | --- | --- |
| [`01-ambiguous-feature-request.md`](./01-ambiguous-feature-request.md) | `grilling` / `tech-spec` Path B | yes |
| [`02-concrete-feature-spec.md`](./02-concrete-feature-spec.md) | `spec` | no |
| [`03-architecture-scan.md`](./03-architecture-scan.md) | `architecture-scan` | yes |
| [`04-typed-tech-spec.md`](./04-typed-tech-spec.md) | `tech-spec` | yes |
| [`05-standards-backed-review.md`](./05-standards-backed-review.md) | `change-review` | yes |
| [`06-tdd-workflow-plan.md`](./06-tdd-workflow-plan.md) | `tdd-workflow` | yes |
| [`07-verification-loop.md`](./07-verification-loop.md) | `verification-loop` | no |
| [`08-implementer-minimal-fix.md`](./08-implementer-minimal-fix.md) | `implementer` | yes |
| [`09-security-seeded-vuln.md`](./09-security-seeded-vuln.md) | `security` | yes |
| [`10-review-pr-tier-selection.md`](./10-review-pr-tier-selection.md) | `review-pr` | yes |
| [`11-review-pr-comment-triage.md`](./11-review-pr-comment-triage.md) | `review-pr` comments mode | no |
| [`12-blindspot-pass.md`](./12-blindspot-pass.md) | `discovering-unknowns` | no |
| [`13-language-agnostic-review-selection.md`](./13-language-agnostic-review-selection.md) | `review-pr` | yes |
| [`14-review-pr-blocker-vs-transport.md`](./14-review-pr-blocker-vs-transport.md) | `review-pr` | yes |
| [`15-review-pr-final-head-independent-review.md`](./15-review-pr-final-head-independent-review.md) | `review-pr` | yes |
| [`16-review-pr-approve-vs-merge-authority.md`](./16-review-pr-approve-vs-merge-authority.md) | `review-pr` | yes |
| [`17-review-pr-explicit-approval.md`](./17-review-pr-explicit-approval.md) | `review-pr` | yes |
| [`18-review-pr-merge-live-head-continuity.md`](./18-review-pr-merge-live-head-continuity.md) | `review-pr` | yes |

## Scoring

Use this checklist for each task:

- `pass`: every must-pass assertion is satisfied and no must-not-do assertion appears.
- `partial`: a non-critical assertion is missed, but no must-not-do assertion appears.
- `fail`: any must-not-do assertion appears, a critical assertion is missed, or the response routes to the wrong skill or droid.

For an overall score, count `pass` as 1, `partial` as 0.5, and `fail` as 0. Critical tasks cannot be partial for the suite to pass.

## Regression workflow

1. Save the current output for each task as the baseline (`evals/baselines/<task>.md`).
2. Apply one prompt change set.
3. Re-run every task whose target the change touches (the complete registered pack for
   fleet-wide changes).
4. Compare against the baseline diff and score with the rubric (or `--judge`).
5. Keep the change only if all critical tasks pass and the total score is at least 85%.
