#!/usr/bin/env bash
# Run one golden task headlessly and (optionally) judge the transcript.
#
#   scripts/run-golden-task.sh <task-file> [--judge] [--exec-model <id>]
#     [--exec-effort <level>] [--judge-model <id>] [--judge-effort <level>]
#     [--droid <droid.md> --model <id> [--effort <level>]] [--label <name>]
#
# What it does:
#   1. Extracts the task's Target, optional ```bash Setup block, and ```text Prompt block.
#   2. Creates a scratch git repo, runs Setup inside it.
#   3. Detects droid targets and runs the headless session on the droid's pinned model with
#      the source prompt as its governing contract. LIMITATION: droid exec has no Task tool,
#      so this is contract execution, not a true subagent invocation or model A/B.
#   4. Invokes `droid exec` against the scratch repo with the composed prompt.
#   5. Writes the transcript to evals/runs/<timestamp>-<task>[-<label>]/transcript.md.
#   6. With --judge: scores the transcript against the task rubric via JUDGE.md.
#   7. Diffs against evals/baselines/<task>.md when a baseline exists.
#
#   (For droid model A/Bs, do NOT use this script — see README "Fable-class models".)
#
# Requires: droid CLI on PATH, the relevant plugins installed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_FILE="${1:?usage: run-golden-task.sh <task-file> [--judge] [--exec-model <id>] [--exec-effort <level>] [--droid <file> --model <id> [--effort <level>]] [--label <name>]}"
shift
JUDGE="" DROID_FILE="" SKILL_FILE="" MODEL="" EFFORT="" LABEL=""
EXEC_MODEL="" EXEC_EFFORT="" JUDGE_MODEL="claude-opus-4-8" JUDGE_EFFORT="xhigh"
while [ $# -gt 0 ]; do
  case "$1" in
    --judge) JUDGE="--judge" ;;
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
TASK_NAME="$(basename "$TASK_FILE" .md)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$ROOT/evals/runs/$STAMP-$TASK_NAME$LABEL"
mkdir -p "$RUN_DIR"

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
[ -n "$PROMPT" ] || { echo "no ## Prompt block found in $TASK_FILE" >&2; exit 1; }

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

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/golden-$TASK_NAME.XXXXXX")"
git -C "$SCRATCH" init -q
if [ -n "$SETUP" ]; then
  (cd "$SCRATCH" && bash -euo pipefail -c "$SETUP")
  git -C "$SCRATCH" add -A && git -C "$SCRATCH" -c user.email=eval@local -c user.name=eval commit -qm "golden-task setup" || true
fi

if [ -n "$DROID_FILE" ]; then
  mkdir -p "$SCRATCH/.factory/droids"
  VARIANT="$SCRATCH/.factory/droids/$(basename "$DROID_FILE")"
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

echo "target: $TARGET"
echo "scratch: $SCRATCH"
echo "run dir: $RUN_DIR"

EXEC_ARGS=()
[ -n "$EXEC_MODEL" ] && EXEC_ARGS+=(--model "$EXEC_MODEL")
[ -n "$EXEC_EFFORT" ] && EXEC_ARGS+=(--reasoning-effort "$EXEC_EFFORT")
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [ "${#EXEC_ARGS[@]}" -gt 0 ]; then
  droid exec "${EXEC_ARGS[@]}" -f "$RUN_DIR/prompt.md" --cwd "$SCRATCH" --auto high -o text \
    | tee "$RUN_DIR/transcript.md"
else
  droid exec -f "$RUN_DIR/prompt.md" --cwd "$SCRATCH" --auto high -o text \
    | tee "$RUN_DIR/transcript.md"
fi
FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

TASK_NAME="$TASK_NAME" TARGET="$TARGET" STARTED_AT="$STARTED_AT" FINISHED_AT="$FINISHED_AT" \
EXEC_MODEL="$EXEC_MODEL" EXEC_EFFORT="$EXEC_EFFORT" DROID_FILE="$DROID_FILE" \
SKILL_FILE="$SKILL_FILE" \
node -e '
  const fs = require("node:fs");
  const metadata = {
    schemaVersion: 1,
    task: process.env.TASK_NAME,
    target: process.env.TARGET,
    startedAt: process.env.STARTED_AT,
    finishedAt: process.env.FINISHED_AT,
    requestedModel: process.env.EXEC_MODEL || null,
    requestedReasoningEffort: process.env.EXEC_EFFORT || null,
    evidenceType: process.env.DROID_FILE || process.env.SKILL_FILE
      ? "source_contract_execution"
      : "headless_execution",
    contractSource: process.env.DROID_FILE || process.env.SKILL_FILE || null,
    pinnedDroidExercised: false
  };
  fs.writeFileSync(process.argv[1], `${JSON.stringify(metadata, null, 2)}\n`);
' "$RUN_DIR/metadata.json"

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
fi

BASELINE="$ROOT/evals/baselines/$TASK_NAME.md"
if [ -f "$BASELINE" ]; then
  echo; echo "--- diff vs accepted baseline (informational) ---"
  diff -u "$BASELINE" "$RUN_DIR/transcript.md" || true
else
  echo; echo "no baseline yet — to accept this run: cp $RUN_DIR/transcript.md $BASELINE"
fi
