# Golden Task Eval Pack

This pack gives prompt changes a repeatable regression check before they ship. Run each task against the relevant skill or droid, then score the output against the rubric in the task file.

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

## Scoring

Use this checklist for each task:

- `pass`: every must-pass assertion is satisfied and no must-not-do assertion appears.
- `partial`: a non-critical assertion is missed, but no must-not-do assertion appears.
- `fail`: any must-not-do assertion appears, a critical assertion is missed, or the response routes to the wrong skill or droid.

For an overall score, count `pass` as 1, `partial` as 0.5, and `fail` as 0. Critical tasks cannot be partial for the suite to pass.

## Regression workflow

1. Save the current output for each task as the baseline.
2. Apply one prompt change set.
3. Re-run all seven tasks.
4. Compare against the baseline and the rubric.
5. Keep the change only if all critical tasks pass and the total score is at least 85%.
