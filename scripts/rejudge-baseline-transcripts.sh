#!/usr/bin/env bash
# Re-judge locally retained baseline transcripts under the CURRENT judge and task rubrics.
#
#   scripts/rejudge-baseline-transcripts.sh [<task-file>...]
#     [--judge-model <id>] [--judge-effort <level>] [--label <name>]
#
# The recalibration path from evals/README.md: after a JUDGE.md or rubric change, score
# the accepted old-prompt transcripts under the new contract to establish per-task floors
# before re-accepting baselines. For each task with a local corpus under
# evals/baselines/transcripts/<task>/, every runN.md is judged against the CURRENT task
# file and JUDGE.md, validated by scripts/judge-contract.mjs, and written to
# evals/results/rejudge-<label>/<task>/runN-verdict.json with a per-task summary.json.
# Everything under evals/results/ is gitignored: floors are local calibration evidence,
# never a committed baseline.
#
# Requires: droid CLI on PATH.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JUDGE_MODEL="claude-opus-4-8" JUDGE_EFFORT="xhigh" LABEL="$(date -u +%Y%m%dT%H%M%SZ)"
TASK_FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --judge-model) JUDGE_MODEL="$2"; shift ;;
    --judge-effort) JUDGE_EFFORT="$2"; shift ;;
    --label) LABEL="$2"; shift ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) TASK_FILES+=("$1") ;;
  esac
  shift
done
if [ "${#TASK_FILES[@]}" -eq 0 ]; then
  for TASK_FILE in "$ROOT"/evals/golden-tasks/[0-9][0-9]-*.md; do
    TASK_NAME="$(basename "$TASK_FILE" .md)"
    [ -d "$ROOT/evals/baselines/transcripts/$TASK_NAME" ] && TASK_FILES+=("$TASK_FILE")
  done
fi
if [ "${#TASK_FILES[@]}" -eq 0 ]; then
  echo "no tasks with a local transcript corpus under evals/baselines/transcripts/" >&2
  exit 1
fi

JUDGE_VERSION="$(awk '/^Version: /{print $2; exit}' "$ROOT/evals/golden-tasks/JUDGE.md")"
OUT_ROOT="$ROOT/evals/results/rejudge-$LABEL"

for TASK_FILE in "${TASK_FILES[@]}"; do
  TASK_NAME="$(basename "$TASK_FILE" .md)"
  TASK_VERSION="$(awk '/^Version: /{print $2; exit}' "$TASK_FILE")"
  CORPUS="$ROOT/evals/baselines/transcripts/$TASK_NAME"
  BASELINE="$ROOT/evals/baselines/$TASK_NAME.json"
  if [ ! -d "$CORPUS" ]; then
    echo "skip $TASK_NAME: no local corpus" >&2
    continue
  fi
  OUT_DIR="$OUT_ROOT/$TASK_NAME"
  mkdir -p "$OUT_DIR"
  echo "=== rejudge $TASK_NAME (task v$TASK_VERSION, judge v$JUDGE_VERSION) ==="
  for TRANSCRIPT in "$CORPUS"/run*.md; do
    RUN_ID="$(basename "$TRANSCRIPT" .md)"
    # The accepting run directory, when retained, carries the post-run repository evidence.
    EVIDENCE=""
    if [ -f "$BASELINE" ]; then
      EVIDENCE="$(BASELINE="$BASELINE" RUN_ID="$RUN_ID" node -e '
        const baseline = JSON.parse(require("node:fs").readFileSync(process.env.BASELINE, "utf8"));
        const index = Number(process.env.RUN_ID.replace("run", "")) - 1;
        process.stdout.write(baseline.runs?.[index]?.runDir ?? "");
      ')"
    fi
    {
      cat "$ROOT/evals/golden-tasks/JUDGE.md"
      echo; echo "--- TASK FILE ---"; cat "$TASK_FILE"
      echo; echo "--- TRANSCRIPT ---"; cat "$TRANSCRIPT"
      echo; echo "--- POST-RUN REPOSITORY EVIDENCE ---"
      if [ -n "$EVIDENCE" ] && [ -f "$ROOT/$EVIDENCE/repository-evidence.md" ]; then
        cat "$ROOT/$EVIDENCE/repository-evidence.md"
      else
        echo "(unavailable for this retained transcript — judge on the transcript alone)"
      fi
    } > "$OUT_DIR/$RUN_ID-judge-prompt.md"
    droid exec --model "$JUDGE_MODEL" --reasoning-effort "$JUDGE_EFFORT" \
      -f "$OUT_DIR/$RUN_ID-judge-prompt.md" -o text | tee "$OUT_DIR/$RUN_ID-verdict.md"
    TASK_NAME="$TASK_NAME" TASK_VERSION="$TASK_VERSION" JUDGE_VERSION="$JUDGE_VERSION" \
    JUDGE_MODEL="$JUDGE_MODEL" JUDGE_EFFORT="$JUDGE_EFFORT" \
    STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    node "$ROOT/scripts/judge-contract.mjs" --task "$TASK_FILE" \
      --verdict-md "$OUT_DIR/$RUN_ID-verdict.md" --out "$OUT_DIR/$RUN_ID-verdict.json"
  done
  OUT_DIR="$OUT_DIR" TASK_NAME="$TASK_NAME" node -e '
    const { readdirSync, readFileSync, writeFileSync } = require("node:fs");
    const dir = process.env.OUT_DIR;
    const score = { pass: 1, partial: 0.5, fail: 0 };
    const verdicts = readdirSync(dir).filter((f) => /-verdict\.json$/.test(f)).sort()
      .map((f) => JSON.parse(readFileSync(`${dir}/${f}`, "utf8")).judge.verdict);
    const summary = {
      task: process.env.TASK_NAME,
      runs: verdicts.length,
      verdicts,
      passRate: verdicts.reduce((sum, verdict) => sum + score[verdict], 0) / (verdicts.length || 1),
      failCount: verdicts.filter((verdict) => verdict === "fail").length,
    };
    writeFileSync(`${dir}/summary.json`, `${JSON.stringify(summary, null, 2)}\n`);
    console.log(`floor ${summary.task}: passRate ${summary.passRate.toFixed(2)} over ${summary.runs} runs (${verdicts.join(", ")})`);
  '
done
echo
echo "floors under: $OUT_ROOT (local only — evals/results/ is gitignored)"
