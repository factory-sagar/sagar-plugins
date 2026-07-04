#!/usr/bin/env bash
# Run one golden task headlessly and (optionally) judge the transcript.
#
#   scripts/run-golden-task.sh evals/golden-tasks/05-standards-backed-review.md [--judge]
#
# What it does:
#   1. Extracts the task's Target, optional ```bash Setup block, and ```text Prompt block.
#   2. Creates a scratch git repo, runs Setup inside it.
#   3. Invokes `droid exec` against the scratch repo with the composed prompt.
#   4. Writes the transcript to evals/runs/<timestamp>-<task>/transcript.md.
#   5. With --judge: scores the transcript against the task rubric via JUDGE.md.
#   6. Diffs against evals/baselines/<task>.md when a baseline exists.
#
# Requires: droid CLI on PATH, the relevant plugins installed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_FILE="${1:?usage: run-golden-task.sh <task-file> [--judge]}"
JUDGE="${2:-}"
TASK_NAME="$(basename "$TASK_FILE" .md)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$ROOT/evals/runs/$STAMP-$TASK_NAME"
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
PROMPT="$(extract_block "Prompt")"
SETUP="$(extract_block "Setup")"
[ -n "$PROMPT" ] || { echo "no ## Prompt block found in $TASK_FILE" >&2; exit 1; }

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/golden-$TASK_NAME.XXXXXX")"
git -C "$SCRATCH" init -q
if [ -n "$SETUP" ]; then
  (cd "$SCRATCH" && bash -euo pipefail -c "$SETUP")
  git -C "$SCRATCH" add -A && git -C "$SCRATCH" -c user.email=eval@local -c user.name=eval commit -qm "golden-task setup" || true
fi

{
  echo "This is a golden-task eval run. Use the \`$TARGET\` skill or droid (via the Task tool if it is a droid) to handle the task below exactly as its prompt specifies. Do not substitute another skill or droid."
  echo
  echo "$PROMPT"
} > "$RUN_DIR/prompt.md"

echo "target: $TARGET"
echo "scratch: $SCRATCH"
echo "run dir: $RUN_DIR"

droid exec -f "$RUN_DIR/prompt.md" --cwd "$SCRATCH" --auto medium -o text \
  | tee "$RUN_DIR/transcript.md"

if [ "$JUDGE" = "--judge" ]; then
  {
    cat "$ROOT/evals/golden-tasks/JUDGE.md"
    echo; echo "--- TASK FILE ---"; cat "$TASK_FILE"
    echo; echo "--- TRANSCRIPT ---"; cat "$RUN_DIR/transcript.md"
  } > "$RUN_DIR/judge-prompt.md"
  droid exec -f "$RUN_DIR/judge-prompt.md" -o text | tee "$RUN_DIR/verdict.md"
fi

BASELINE="$ROOT/evals/baselines/$TASK_NAME.md"
if [ -f "$BASELINE" ]; then
  echo; echo "--- diff vs accepted baseline (informational) ---"
  diff -u "$BASELINE" "$RUN_DIR/transcript.md" || true
else
  echo; echo "no baseline yet — to accept this run: cp $RUN_DIR/transcript.md $BASELINE"
fi
