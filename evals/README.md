# Eval System

Regression evidence for every prompt surface in this marketplace. Three tiers, baselined
differently because they cost differently:

| Tier | What runs | Baseline | When it runs |
| --- | --- | --- | --- |
| Deterministic | `scripts/validate.mjs`, `scripts/validate-evals.mjs`, guardrail unittests, review selector tests | green CI | every push and PR |
| Routing | `routing/cases.json` scored by `scripts/eval-routing.mjs` against `policy.json` | thresholds in `policy.json` | when router vocabulary, AGENTS routing rules, or workflow descriptions change |
| Judged golden tasks | `golden-tasks/*.md` via `scripts/run-golden-task.sh --judge`; verdicts validated by `scripts/judge-contract.mjs` for axis coverage and derived-verdict recomputation | accepted verdict baselines in `baselines/` | when a task's `## Target` contract changes |
| Fix-pair recall | real mined defect pairs via `scripts/run-review-fixpairs.mjs` + `scripts/score-fixpairs.mjs` | none: each mined corpus is its own ground truth | when evaluating droid model candidates on real regressions |

## Verdict baselines, not transcript baselines

Two good runs of a stochastic system differ textually every time, so transcripts are never
compared. The comparable unit is the judged verdict:

1. `scripts/run-golden-task.sh <task> --judge` writes `verdict.json` per run, stamped with
   the task `Version:`, the `JUDGE.md` `Version:`, the judge model, and the SHA-256 of the
   governing contract file. `scripts/judge-contract.mjs` validates axis coverage and
   recomputes the derived verdict.
2. `scripts/accept-baseline.sh <task>` runs the task N times (default:
   `policy.json` `repetitions.promptChange`), requires every verdict to parse, and writes
   `baselines/<task>.json` plus accepted local transcripts under `baselines/transcripts/`.
   Commit the JSON, which is the floor. The transcripts stay local and gitignored: they are
   model output produced on one machine and this repository is public. They remain the
   judge-recalibration corpus for whoever accepted them.
3. `scripts/compare-baseline.mjs <task> <verdict.json>...` exits nonzero on regression:
   candidate pass rate below the baseline pass rate, or a new `fail` against a zero-fail
   baseline.

## When a baseline stops being comparable

A verdict is only comparable while the rubric, judge, and contract are constant.
`compare-baseline.mjs` refuses (exit 3) instead of comparing when any of these differ from
the baseline:

- **Task version** — any golden-task edit bumps its `Version:` line (CI enforces this on
  PRs). Re-accept the baseline after the change.
- **Judge version or judge model** — after changing `JUDGE.md` or the judge pin, run
  `scripts/rejudge-baseline-transcripts.sh` on your local baseline transcripts to recalibrate,
  then re-accept. Without a local corpus, re-accept from scratch instead.
- **Contract hash** — the target droid/skill file changed. Rerun only the tasks whose
  `## Target` maps to the changed file, then re-accept the ones that moved intentionally.

CI enforces these comparability rules on PRs whenever a targeted contract or `JUDGE.md` changes.
Fix a freshness failure with `scripts/accept-baseline.sh evals/golden-tasks/<task>.md`.

A differing exec model stays comparable and is flagged (`modelChanged`) — that is the
model-A/B path. Apply `policy.json` `modelDecision` rules to the comparison output and
record the outcome in `model-decisions/`, then update `model-assignments.json`
(`scripts/validate.mjs` keeps the registry, droid frontmatter, and README table in sync).

## Honesty limits

`droid exec` has no Task tool, so droid-targeted golden tasks measure source-contract
adherence, not deployed subagent behavior; every run records
`"pinnedDroidExercised": false`. Treat single-run differences as noise: acceptance uses
N repeats, and `repetitions.modelChange` governs model comparisons.

## Fix-pair recall tier (real-world model evaluation)

The golden tier measures contract adherence on curated tasks; the fix-pair tier measures
defect recall against real regressions mined from a private monorepo's merged history.
`scripts/mine-fix-pairs.mjs --repo <clone> --gh-repo <owner/name>` finds merged fix PRs,
blames the pre-fix tree to attribute the introducing ("culprit") PR, and emits
`tmp/fixpairs/corpus.json` plus a human review sheet.
Both stay local: the corpus contains private repo content and is gitignored.

`scripts/run-review-fixpairs.mjs --corpus <file> --repo <clone> --role <droid> --model <m>
[--effort e] [--reps n] [--pairs fp-0001,...]` reviews each culprit diff in a detached
worktree of the private clone and records findings, cost, and latency per run under
`evals/runs/`.
`scripts/score-fixpairs.mjs` classifies each finding (`hit` / `near-miss` / `outside` /
`unlocated`) against the labeled defect regions and prints a role × model scorecard; its
JSON output feeds `scripts/model-decision.mjs` under `policy.json` `modelDecision`
thresholds exactly like the golden tier.

Honesty limits specific to this tier: attribution is heuristic (fix authors most often fix
their own PRs; `high` confidence means every blamed line resolved to one PR), pairs are
defect-true but not defect-complete, so the metric is recall per labeled region plus
outside-region noise, never precision against "all defects in the diff". Pairs below
`medium` confidence never feed decisions.

## Layout

- `golden-tasks/` — versioned task rubrics plus `JUDGE.md` (the scoring contract)
- `scripts/judge-contract.mjs` — validates judged-task axis coverage and derived verdicts
- `scripts/rejudge-baseline-transcripts.sh` — recalibrates local baseline transcripts
- `scripts/mine-fix-pairs.mjs`, `run-review-fixpairs.mjs`, `score-fixpairs.mjs` — the
  fix-pair tier; the mined corpus lives in `tmp/fixpairs/` and stays local
- `baselines/` — accepted verdict baselines (committed); `baselines/transcripts/` (local only)
- `routing/cases.json` — intent-routing cases (also asserted deterministically by the
  guardrails test suite)
- `policy.json` — thresholds: routing gates, repetition counts, model-decision rules
- `model-assignments.json` — per-droid model registry, CI-synced to frontmatter
- `model-decisions/` — evidence records behind every registry entry
- `runs/`, `results/` — generated output, gitignored
