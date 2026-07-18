# Golden Task Baselines

Accepted transcripts, one per task, named `<task-file-stem>.md`
(e.g. `05-standards-backed-review.md`).

- Accept a run: `cp evals/runs/<stamp>-<task>/transcript.md evals/baselines/<task>.md`
- `scripts/run-golden-task.sh` diffs each new run against its baseline automatically
  (informational — the rubric verdict, not the diff, decides pass/fail).
- Update a baseline only when a prompt change is intentional and the new transcript passed
  the rubric. The baseline diff exists so a prompt regression is visible as a diff in review,
  not discovered in production.

Transient run output lives in `evals/runs/` (gitignored); baselines are committed.
