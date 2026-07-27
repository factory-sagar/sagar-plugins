#!/usr/bin/env bash
# Accept a verdict-level baseline for one golden task.
#
#   scripts/accept-baseline.sh <task-file> [--runs N] [--exec-model <id>]
#     [--exec-effort <level>] [--judge-model <id>] [--judge-effort <level>]
#
# Runs the task N times (default: evals/policy.json repetitions.promptChange)
# with --judge, requires every verdict to parse, then writes:
#   evals/baselines/<task>.json                  the accepted verdict baseline (committed)
#   evals/baselines/transcripts/<task>/runN.md   the accepted transcripts (LOCAL ONLY,
#     gitignored: they are model output produced on this machine and the repository is
#     public. They remain the judge-recalibration corpus for whoever accepted them.)
#
# A baseline is only comparable at the same task version, judge version, judge
# model, and contract hash; scripts/compare-baseline.mjs enforces that.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_FILE="${1:?usage: accept-baseline.sh <task-file> [--runs N] [runner flags]}"
shift
RUNS="$(python3 -c 'import json; print(json.load(open("'"$ROOT"'/evals/policy.json"))["repetitions"]["promptChange"])')"
PASSTHROUGH=()
while [ $# -gt 0 ]; do
  case "$1" in
    --runs) RUNS="$2"; shift ;;
    *) PASSTHROUGH+=("$1") ;;
  esac
  shift
done
case "$RUNS" in (''|*[!0-9]*|0) echo "--runs must be a positive integer" >&2; exit 2 ;; esac

TASK_NAME="$(basename "$TASK_FILE" .md)"
LABEL="accept$(date -u +%s)"
if [ "${#PASSTHROUGH[@]}" -gt 0 ]; then
  "$ROOT/scripts/run-golden-task.sh" "$TASK_FILE" --judge --runs "$RUNS" --label "$LABEL" "${PASSTHROUGH[@]}"
else
  "$ROOT/scripts/run-golden-task.sh" "$TASK_FILE" --judge --runs "$RUNS" --label "$LABEL"
fi

ROOT="$ROOT" TASK_NAME="$TASK_NAME" LABEL="$LABEL" RUNS="$RUNS" python3 - <<'PYEOF'
import glob
import json
import os
import shutil
import sys
import time

root = os.environ["ROOT"]
task = os.environ["TASK_NAME"]
label = os.environ["LABEL"]
expected_runs = int(os.environ["RUNS"])

pattern = f"{root}/evals/runs/*-{task}-{label}*/verdict.json"
verdict_files = sorted(glob.glob(pattern))
if len(verdict_files) != expected_runs:
    sys.stderr.write(
        f"expected {expected_runs} verdicts, found {len(verdict_files)} for {pattern}\n"
    )
    sys.exit(1)

verdicts = [json.load(open(f, encoding="utf-8")) for f in verdict_files]
identity_fields = (
    "taskVersion",
    "judgeVersion",
    "judgeModel",
    "judgeReasoningEffort",
    "execModel",
    "execReasoningEffort",
    "contractSource",
    "contractSha",
)
for field in identity_fields:
    values = {json.dumps(v.get(field)) for v in verdicts}
    if len(values) != 1:
        sys.stderr.write(f"verdicts disagree on {field}: {sorted(values)}\n")
        sys.exit(1)

score = {"pass": 1.0, "partial": 0.5, "fail": 0.0}
outcomes = [v["judge"]["verdict"] for v in verdicts]
pass_rate = sum(score[outcome] for outcome in outcomes) / len(outcomes)

transcripts_dir = f"{root}/evals/baselines/transcripts/{task}"
shutil.rmtree(transcripts_dir, ignore_errors=True)
os.makedirs(transcripts_dir, exist_ok=True)
runs = []
for index, verdict_file in enumerate(verdict_files, start=1):
    run_dir = os.path.dirname(verdict_file)
    transcript_rel = f"transcripts/{task}/run{index}.md"
    shutil.copyfile(f"{run_dir}/transcript.md", f"{root}/evals/baselines/{transcript_rel}")
    runs.append(
        {
            "runDir": os.path.relpath(run_dir, root),
            "verdict": verdicts[index - 1]["judge"]["verdict"],
            "transcript": transcript_rel,
        }
    )

baseline = {
    "schemaVersion": 1,
    "task": task,
    **{field: verdicts[0].get(field) for field in identity_fields},
    "acceptedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "runs": runs,
    "passRate": pass_rate,
    "failCount": outcomes.count("fail"),
}
baseline_path = f"{root}/evals/baselines/{task}.json"
with open(baseline_path, "w", encoding="utf-8") as stream:
    json.dump(baseline, stream, indent=2)
    stream.write("\n")
print(f"accepted baseline: {baseline_path} (passRate {pass_rate:.2f} over {len(runs)} runs)")
print("commit the baseline JSON; transcripts stay local (gitignored)")
PYEOF
