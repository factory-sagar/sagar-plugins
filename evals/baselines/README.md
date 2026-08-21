# Golden Task Baselines

Accepted **verdict** baselines, one JSON per task (`<task-file-stem>.json`), plus the
accepted local transcripts under `transcripts/<task>/runN.md`. Transcripts are gitignored,
never committed or diffed as a pass/fail signal, and remain the judge-recalibration corpus for
the accepting machine.

- Accept: `scripts/accept-baseline.sh evals/golden-tasks/<task>.md` (N judged runs,
  default from `evals/policy.json` `repetitions.promptChange`).
- Compare: `node scripts/compare-baseline.mjs <task> <verdict.json>...` — exit 1 on a
  pass-rate drop or a new `fail`, exit 3 when task/judge/contract versions make the runs
  incomparable (that means re-baseline, not compare).
- Re-accept only when a prompt or rubric change is intentional and the new runs passed;
  the acceptance commit is where a reviewer sees the behavior change.

Schema and comparability rules: `evals/README.md`. Transient run output stays in
`evals/runs/` (gitignored).
