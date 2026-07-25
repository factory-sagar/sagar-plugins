# Golden Task Eval Pack

This pack gives prompt changes a repeatable regression check before they ship. Run each task against the relevant skill or droid, then score the output against the rubric in the task file.

Run a task headlessly with `scripts/run-golden-task.sh <task-file> [--judge] [--runs N]`: it extracts the task's optional ` ```bash ` Setup block into a scratch git repo, runs the ` ```text ` Prompt via `droid exec`, saves the transcript under `evals/runs/`, and with `--judge` scores the transcript plus post-run repository evidence against [`JUDGE.md`](./JUDGE.md), writing a version-stamped `verdict.json` per run. Accepted verdict baselines live in [`../baselines/`](../baselines/); see [`../README.md`](../README.md) for the baseline and comparability rules.

Every task file carries a `Version: N` line. Bump it on any rubric change (CI enforces this on PRs); verdicts are only comparable at a pinned task version.

The runner detects skill and droid targets and supplies the installed source prompt as the
governing contract. Droid-targeted tasks run inline because `droid exec` has no Task tool; the
runner also selects the droid's pinned model and reasoning effort. These runs measure headless
source-contract adherence, not subagent transport or a true Task invocation. Model A/Bs for
droids still run in-session via the Task tool.

## Pass rule

- All critical tasks must pass.
- No output may violate a must-not-do rule.
- Overall score must be at least 85%.

Coverage floor: every public workflow has at least one task, and every droid whose failure
is expensive has one. `scripts/validate-evals.mjs` warns on droids with zero tasks.

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
| [`15-review-pr-convergent-loop-review.md`](./15-review-pr-convergent-loop-review.md) | `review-pr` | yes |
| [`16-review-pr-approve-vs-merge-authority.md`](./16-review-pr-approve-vs-merge-authority.md) | `review-pr` | yes |
| [`17-review-pr-explicit-approval.md`](./17-review-pr-explicit-approval.md) | `review-pr` | yes |
| [`18-review-pr-merge-live-head-continuity.md`](./18-review-pr-merge-live-head-continuity.md) | `review-pr` | yes |
| [`19-ship-delivery-sequence.md`](./19-ship-delivery-sequence.md) | `ship` | yes |
| [`20-commit-message-writer.md`](./20-commit-message-writer.md) | `commit-message-writer` | no |
| [`21-pr-describer-self-contained.md`](./21-pr-describer-self-contained.md) | `pr-describer` | no |
| [`22-planner-decomposition.md`](./22-planner-decomposition.md) | `planner` | yes |
| [`23-debugger-rca-no-patch.md`](./23-debugger-rca-no-patch.md) | `debugger` | yes |
| [`24-quick-analysis-triage.md`](./24-quick-analysis-triage.md) | `quick-analysis` | no |
| [`25-doc-generator-minimal-edit.md`](./25-doc-generator-minimal-edit.md) | `doc-generator` | no |
| [`26-prompt-optimizer-audit.md`](./26-prompt-optimizer-audit.md) | `prompt-optimizer` | no |

## Scoring

Use this checklist for each task:

- `pass`: every must-pass assertion is satisfied and no must-not-do assertion appears.
- `partial`: a non-critical assertion is missed, but no must-not-do assertion appears.
- `fail`: any must-not-do assertion appears, a critical assertion is missed, or the response routes to the wrong skill or droid.

For an overall score, count `pass` as 1, `partial` as 0.5, and `fail` as 0. Critical tasks cannot be partial for the suite to pass.

## Regression workflow

1. Accept a verdict baseline for each task (`scripts/accept-baseline.sh <task-file>`,
   N judged runs) and commit `evals/baselines/<task>.json` plus its transcripts.
2. Apply one prompt change set.
3. Re-run every task whose target the change touches (the complete registered pack for
   fleet-wide changes): `scripts/run-golden-task.sh <task-file> --judge --runs N`.
4. Gate with `node scripts/compare-baseline.mjs <task> <verdict.json>...` — a pass-rate
   drop or a new `fail` is a regression; a version or contract mismatch means
   re-baseline, not compare.
5. Keep the change only if all critical tasks pass and the total score is at least 85%;
   re-accept baselines for intentional behavior changes in the same PR.
