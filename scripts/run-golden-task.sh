#!/usr/bin/env bash
# Run one golden task headlessly and (optionally) judge the transcript.
#
#   scripts/run-golden-task.sh <task-file> [--judge] [--runs N] [--exec-model <id>]
#     [--exec-effort <level>] [--judge-model <id>] [--judge-effort <level>]
#     [--droid <droid.md> --model <id> [--effort <level>]] [--label <name>]
#
# What it does, once per run (--runs N repeats with fresh scratch state):
#   1. Extracts the task's Target, Version, optional ```bash Setup block, and ```text Prompt block.
#   2. Creates a scratch git repo, runs Setup inside it.
#   3. Detects droid targets and runs the headless session on the droid's pinned model with
#      the source prompt as its governing contract. LIMITATION: droid exec has no Task tool,
#      so this is contract execution, not a true subagent invocation or model A/B.
#   4. Invokes `droid exec` against the scratch repo with the composed prompt.
#   5. Writes the transcript to evals/runs/<timestamp>-<task>[-<label>][-rN]/transcript.md.
#   6. With --judge: scores the transcript against the task rubric via JUDGE.md and writes
#      the parsed verdict, stamped with task/judge versions and the contract hash, to
#      verdict.json (the comparable unit for baselines - see scripts/compare-baseline.mjs).
#
# Baselines are verdict-level, not transcript-level: accept with
# scripts/accept-baseline.sh, compare with scripts/compare-baseline.mjs.
# (For droid model A/Bs, see evals/README.md "Honesty limits": --droid/--model runs are
# source-contract execution, not deployed subagent behavior; decisions land via the
# modelDecision path with scripts/model-decision.mjs and evals/model-decisions/ records.)
#
# Requires: droid CLI on PATH, the relevant plugins installed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_FILE="${1:?usage: run-golden-task.sh <task-file> [--judge] [--runs N] [--exec-model <id>] [--exec-effort <level>] [--droid <file> --model <id> [--effort <level>]] [--label <name>]}"
shift
JUDGE="" DROID_FILE="" SKILL_FILE="" MODEL="" EFFORT="" LABEL="" RUNS=1
EXEC_MODEL="" EXEC_EFFORT="" JUDGE_MODEL="claude-opus-4-8" JUDGE_EFFORT="xhigh"
while [ $# -gt 0 ]; do
  case "$1" in
    --judge) JUDGE="--judge" ;;
    --runs) RUNS="$2"; shift ;;
    --droid) DROID_FILE="$2"; shift ;;
    --model) MODEL="$2"; shift ;;
    --effort) EFFORT="$2"; shift ;;
    --exec-model) EXEC_MODEL="$2"; shift ;;
    --exec-effort) EXEC_EFFORT="$2"; shift ;;
    --judge-model) JUDGE_MODEL="$2"; shift ;;
    --judge-effort) JUDGE_EFFORT="$2"; shift ;;
    --label) LABEL="-$2"; shift ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
  shift
done
if [ -n "$DROID_FILE" ] && [ -z "$MODEL" ]; then echo "--droid requires --model" >&2; exit 2; fi
case "$RUNS" in (''|*[!0-9]*|0) echo "--runs must be a positive integer" >&2; exit 2 ;; esac
TASK_NAME="$(basename "$TASK_FILE" .md)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# Extract the first fenced block that follows a given H2 heading.
extract_block() { # $1=heading
  awk -v h="## $1" '
    $0 == h { hunt = 1; next }
    hunt && /^```/ { if (inblock) exit; inblock = 1; next }
    inblock { print }
  ' "$TASK_FILE"
}

TARGET="$(awk '/^## Target/{getline; while ($0 ~ /^$/) getline; print; exit}' "$TASK_FILE" | tr -d '`.')"
TARGET_NAME="${TARGET%% *}"
PROMPT="$(extract_block "Prompt")"
SETUP="$(extract_block "Setup")"
TASK_VERSION="$(awk '/^Version: /{print $2; exit}' "$TASK_FILE")"
JUDGE_VERSION="$(awk '/^Version: /{print $2; exit}' "$ROOT/evals/golden-tasks/JUDGE.md")"
[ -n "$PROMPT" ] || { echo "no ## Prompt block found in $TASK_FILE" >&2; exit 1; }
[ -n "$TASK_VERSION" ] || { echo "no 'Version: N' line found in $TASK_FILE" >&2; exit 1; }

if [ -z "$DROID_FILE" ]; then
  for CANDIDATE in "$ROOT"/plugins/*/droids/"$TARGET_NAME.md"; do
    if [ -f "$CANDIDATE" ]; then
      DROID_FILE="${CANDIDATE#"$ROOT/"}"
      MODEL="$(awk '/^model: / { print $2; exit }' "$CANDIDATE")"
      EFFORT="$(awk '/^reasoningEffort: / { print $2; exit }' "$CANDIDATE")"
      [ -n "$EXEC_MODEL" ] || EXEC_MODEL="$MODEL"
      [ -n "$EXEC_EFFORT" ] || EXEC_EFFORT="$EFFORT"
      break
    fi
  done
fi

if [ -z "$DROID_FILE" ]; then
  for CANDIDATE in "$ROOT"/plugins/*/skills/"$TARGET_NAME"/SKILL.md; do
    if [ -f "$CANDIDATE" ]; then
      SKILL_FILE="${CANDIDATE#"$ROOT/"}"
      break
    fi
  done
fi

CONTRACT_SOURCE="${DROID_FILE:-$SKILL_FILE}"
CONTRACT_SHA=""
if [ -n "$CONTRACT_SOURCE" ]; then
  CONTRACT_SHA="$(shasum -a 256 "$ROOT/$CONTRACT_SOURCE" | awk '{print $1}')"
fi

run_once() { # $1=run index
  local RUN_SUFFIX=""
  [ "$RUNS" -gt 1 ] && RUN_SUFFIX="-r$1"
  local RUN_DIR="$ROOT/evals/runs/$STAMP-$TASK_NAME$LABEL$RUN_SUFFIX"
  mkdir -p "$RUN_DIR"

  local SCRATCH
  SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/golden-$TASK_NAME.XXXXXX")"
  git -C "$SCRATCH" init -q
  if [ -n "$SETUP" ]; then
    (cd "$SCRATCH" && bash -euo pipefail -c "$SETUP")
    git -C "$SCRATCH" add -A && git -C "$SCRATCH" -c user.email=eval@local -c user.name=eval commit -qm "golden-task setup" || true
  fi

  if [ -n "$DROID_FILE" ]; then
    mkdir -p "$SCRATCH/.factory/droids"
    local VARIANT="$SCRATCH/.factory/droids/$(basename "$DROID_FILE")"
    awk -v model="$MODEL" -v effort="$EFFORT" '
      /^model: / { print "model: " model; if (effort != "") { print "reasoningEffort: " effort; skip_effort = 1 }; next }
      /^reasoningEffort: / && skip_effort { next }
      { print }
    ' "$ROOT/$DROID_FILE" > "$VARIANT"
    echo "droid variant: $(basename "$DROID_FILE" .md) -> $MODEL${EFFORT:+ ($EFFORT)} (project override in scratch repo)"
  fi

  {
    if [ -n "$DROID_FILE" ]; then
      echo "This is a golden-task contract eval for the \`$TARGET_NAME\` droid. The headless runner has no Task tool, so read \`$ROOT/$DROID_FILE\` and perform the task inline under that governing contract. Load any contract-relative references from the source location. Do not block merely because the droid or Task tool is unavailable, and do not substitute another reviewer."
    elif [ -n "$SKILL_FILE" ]; then
      echo "This is a golden-task contract eval for the \`$TARGET_NAME\` skill. Read \`$ROOT/$SKILL_FILE\` and perform the task inline under that governing contract. Load any contract-relative references from the source location. Do not substitute another skill or droid."
    else
      echo "This is a golden-task eval run. Use the \`$TARGET\` skill to handle the task below exactly as its prompt specifies. Do not substitute another skill or droid."
    fi
    echo
    echo "$PROMPT"
  } > "$RUN_DIR/prompt.md"

  echo "target: $TARGET (task v$TASK_VERSION, judge v$JUDGE_VERSION)"
  echo "scratch: $SCRATCH"
  echo "run dir: $RUN_DIR"

  local EXEC_ARGS=()
  [ -n "$EXEC_MODEL" ] && EXEC_ARGS+=(--model "$EXEC_MODEL")
  [ -n "$EXEC_EFFORT" ] && EXEC_ARGS+=(--reasoning-effort "$EXEC_EFFORT")
  local STARTED_AT FINISHED_AT
  STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  # `-o json` returns one final result object: `.result` is the same final-message text that
  # `-o text` prints, and `.usage`/`.duration_ms` carry cost and latency for model decisions.
  # ${arr[@]+"${arr[@]}"} keeps an empty EXEC_ARGS legal under `set -u` on bash 3.2 (macOS).
  droid exec ${EXEC_ARGS[@]+"${EXEC_ARGS[@]}"} -f "$RUN_DIR/prompt.md" --cwd "$SCRATCH" --auto high -o json \
    > "$RUN_DIR/exec-result.json"
  FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  node -e '
    const fs = require("node:fs");
    const [rawPath, transcriptPath] = process.argv.slice(1);
    const raw = fs.readFileSync(rawPath, "utf8");
    let parsed = null;
    try { parsed = JSON.parse(raw); } catch { parsed = null; }
    const text = parsed && typeof parsed.result === "string" ? parsed.result : raw;
    fs.writeFileSync(transcriptPath, text.endsWith("\n") ? text : `${text}\n`);
  ' "$RUN_DIR/exec-result.json" "$RUN_DIR/transcript.md"
  cat "$RUN_DIR/transcript.md"

  TASK_NAME="$TASK_NAME" TARGET="$TARGET" STARTED_AT="$STARTED_AT" FINISHED_AT="$FINISHED_AT" \
  EXEC_MODEL="$EXEC_MODEL" EXEC_EFFORT="$EXEC_EFFORT" DROID_FILE="$DROID_FILE" \
  SKILL_FILE="$SKILL_FILE" TASK_VERSION="$TASK_VERSION" JUDGE_VERSION="$JUDGE_VERSION" \
  CONTRACT_SHA="$CONTRACT_SHA" \
  node -e '
    const fs = require("node:fs");
    const metadata = {
      schemaVersion: 2,
      task: process.env.TASK_NAME,
      taskVersion: Number(process.env.TASK_VERSION),
      judgeVersion: Number(process.env.JUDGE_VERSION) || null,
      target: process.env.TARGET,
      startedAt: process.env.STARTED_AT,
      finishedAt: process.env.FINISHED_AT,
      requestedModel: process.env.EXEC_MODEL || null,
      requestedReasoningEffort: process.env.EXEC_EFFORT || null,
      evidenceType: process.env.DROID_FILE || process.env.SKILL_FILE
        ? "source_contract_execution"
        : "headless_execution",
      contractSource: process.env.DROID_FILE || process.env.SKILL_FILE || null,
      contractSha: process.env.CONTRACT_SHA || null,
      pinnedDroidExercised: false
    };
    try {
      const execResult = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
      metadata.usage = execResult.usage ?? null;
      metadata.execDurationMs = execResult.duration_ms ?? null;
    } catch {
      metadata.usage = null;
      metadata.execDurationMs = null;
    }
    fs.writeFileSync(process.argv[1], `${JSON.stringify(metadata, null, 2)}\n`);
  ' "$RUN_DIR/metadata.json" "$RUN_DIR/exec-result.json"

  if [ "$JUDGE" = "--judge" ]; then
    {
      echo "# Post-run repository evidence"
      echo
      echo "## Status"
      git -C "$SCRATCH" status --short
      echo
      echo "## Commit history and patches"
      git -C "$SCRATCH" log --reverse --format='commit %H%nAuthor: %an <%ae>%nDate: %aI%n%n    %s%n%n%b' --stat --patch --all
      echo
      echo "## Uncommitted diff"
      git -C "$SCRATCH" diff
    } > "$RUN_DIR/repository-evidence.md"
    {
      cat "$ROOT/evals/golden-tasks/JUDGE.md"
      echo; echo "--- TASK FILE ---"; cat "$TASK_FILE"
      echo; echo "--- TRANSCRIPT ---"; cat "$RUN_DIR/transcript.md"
      echo; echo "--- POST-RUN REPOSITORY EVIDENCE ---"; cat "$RUN_DIR/repository-evidence.md"
    } > "$RUN_DIR/judge-prompt.md"
    droid exec --model "$JUDGE_MODEL" --reasoning-effort "$JUDGE_EFFORT" \
      -f "$RUN_DIR/judge-prompt.md" -o text | tee "$RUN_DIR/verdict.md"

    RUN_DIR="$RUN_DIR" TASK_NAME="$TASK_NAME" TASK_VERSION="$TASK_VERSION" \
    JUDGE_VERSION="$JUDGE_VERSION" JUDGE_MODEL="$JUDGE_MODEL" JUDGE_EFFORT="$JUDGE_EFFORT" \
    EXEC_MODEL="$EXEC_MODEL" EXEC_EFFORT="$EXEC_EFFORT" CONTRACT_SOURCE="$CONTRACT_SOURCE" \
    CONTRACT_SHA="$CONTRACT_SHA" STARTED_AT="$STARTED_AT" FINISHED_AT="$FINISHED_AT" \
    python3 - <<'PYEOF'
import json
import os
import re
import sys

run_dir = os.environ["RUN_DIR"]
text = open(f"{run_dir}/verdict.md", encoding="utf-8").read()
fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
candidate = fenced[-1] if fenced else None
if candidate is None:
    start = text.rfind('{\n  "task"')
    if start == -1:
        start = text.rfind("{")
    depth = 0
    end = None
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    candidate = text[start:end] if start != -1 and end else None
try:
    verdict = json.loads(candidate) if candidate else None
except json.JSONDecodeError:
    verdict = None
if not isinstance(verdict, dict) or verdict.get("verdict") not in {"pass", "partial", "fail"}:
    sys.stderr.write("could not parse a judge verdict JSON block from verdict.md\n")
    sys.exit(1)
record = {
    "schemaVersion": 1,
    "task": os.environ["TASK_NAME"],
    "taskVersion": int(os.environ["TASK_VERSION"]),
    "judgeVersion": int(os.environ["JUDGE_VERSION"]) if os.environ.get("JUDGE_VERSION") else None,
    "judgeModel": os.environ["JUDGE_MODEL"],
    "judgeReasoningEffort": os.environ["JUDGE_EFFORT"],
    "execModel": os.environ.get("EXEC_MODEL") or None,
    "execReasoningEffort": os.environ.get("EXEC_EFFORT") or None,
    "contractSource": os.environ.get("CONTRACT_SOURCE") or None,
    "contractSha": os.environ.get("CONTRACT_SHA") or None,
    "startedAt": os.environ["STARTED_AT"],
    "finishedAt": os.environ["FINISHED_AT"],
    "judge": verdict,
}
with open(f"{run_dir}/verdict.json", "w", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(f"verdict: {verdict['verdict']} -> {run_dir}/verdict.json")
PYEOF
  fi
}

for RUN_INDEX in $(seq 1 "$RUNS"); do
  [ "$RUNS" -gt 1 ] && echo "=== run $RUN_INDEX of $RUNS ==="
  run_once "$RUN_INDEX"
done

BASELINE="$ROOT/evals/baselines/$TASK_NAME.json"
if [ -f "$BASELINE" ]; then
  echo
  echo "baseline exists — compare judged runs with:"
  echo "  node scripts/compare-baseline.mjs $TASK_NAME evals/runs/$STAMP-$TASK_NAME$LABEL*/verdict.json"
else
  echo
  echo "no baseline yet — accept one with: scripts/accept-baseline.sh $TASK_FILE"
fi
