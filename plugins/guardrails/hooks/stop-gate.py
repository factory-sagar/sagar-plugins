#!/usr/bin/env python3
"""Stop guardrail: single-nudge verification gate.

If files were modified this session and no verification command (tests,
lint, typecheck, build) ran after the last edit, block the stop once and
tell Droid to run verification. The nudge fires at most once per stop
cycle: when stop_hook_active is true the gate always allows.

Allows immediately when:
- GUARDRAILS_DISABLE=1 or GUARDRAILS_STOP_GATE=off is set
- the project opts out via a .factory/guardrails-off marker file
- no edits happened (research/Q&A sessions)
- only documentation files were edited
- verification evidence exists after the last edit

Edits are detected from Edit/Create/ApplyPatch/MultiEdit tool calls and
from Task delegations to the implementer or test-engineer droids.
Verification evidence is an Execute call (or a Task delegation whose
prompt clearly runs verification) that did not fail.
"""
import json
import os
import re
import sys

EDIT_TOOLS = {"Edit", "Create", "ApplyPatch", "MultiEdit"}
EDITING_SUBAGENTS = {"implementer", "test-engineer"}
DOC_SUFFIXES = (".md", ".mdx", ".txt", ".rst")

VERIFY_PATTERNS = [
    r"\b(npm|pnpm|yarn|bun)\b[^|;&]*\b(test|lint|typecheck|type-check|build|check)\b",
    r"\bnpx\s+(vitest|jest|tsc|eslint|playwright)\b",
    r"\b(vitest|jest|mocha)\b",
    r"\btsc\b",
    r"\beslint\b",
    r"\bpytest\b",
    r"\bpython3?\s+-m\s+pytest\b",
    r"\bruff\b",
    r"\bmypy\b",
    r"\bgo\s+(test|vet|build)\b",
    r"\bcargo\s+(test|check|clippy|build)\b",
    r"\bmake\s+(test|check|lint|build|verify)\b",
    r"\b(gradle|gradlew|mvn)\b[^|;&]*\b(test|verify|check|build)\b",
    r"\bdotnet\s+(test|build)\b",
    r"\bswift\s+(test|build)\b",
    r"\bmix\s+test\b",
    r"\brspec\b",
    r"\bphpunit\b",
]

NUDGE = (
    "Guardrails verification gate: files were modified this session but no "
    "verification command (tests / lint / typecheck / build) ran after the "
    "last edit. Run the project's verification now, fix anything it surfaces, "
    "then finish. If this project has no verification commands or they are "
    "genuinely not applicable, state that briefly and finish. This gate "
    "nudges only once."
)


def allow():
    sys.exit(0)


def matches_verify(text):
    return any(re.search(p, text) for p in VERIFY_PATTERNS)


def result_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def result_failed(entry):
    if entry is None:
        return True
    is_error, text = entry
    if is_error:
        return True
    # Only trust the trailing harness marker; earlier matches may come from
    # the command's own output (e.g. a test log quoting an exit code).
    codes = re.findall(r"\[Process exited with code (\d+)\]", text)
    return bool(codes and codes[-1] != "0")


def main():
    if os.environ.get("GUARDRAILS_DISABLE") or os.environ.get("GUARDRAILS_STOP_GATE") == "off":
        allow()
    try:
        data = json.load(sys.stdin)
    except Exception:
        allow()
    if data.get("stop_hook_active"):
        allow()
    cwd = data.get("cwd") or ""
    if cwd and os.path.exists(os.path.join(cwd, ".factory", "guardrails-off")):
        allow()
    transcript = os.path.expanduser(data.get("transcript_path") or "")
    if not transcript or not os.path.isfile(transcript):
        allow()

    idx = 0
    last_edit_idx = -1
    edited_paths = []
    unknown_edit = False
    candidates = []  # (idx, tool_use_id)
    results = {}     # tool_use_id -> (is_error, text)

    with open(transcript, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("type") != "message":
                continue
            content = (obj.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "tool_use":
                    idx += 1
                    name = block.get("name", "")
                    tool_input = block.get("input") or {}
                    if name in EDIT_TOOLS:
                        last_edit_idx = idx
                        path = tool_input.get("file_path")
                        if path:
                            edited_paths.append(path)
                        else:
                            unknown_edit = True
                    elif name == "Execute":
                        if matches_verify(tool_input.get("command") or ""):
                            candidates.append((idx, block.get("id")))
                    elif name == "Task":
                        subagent = tool_input.get("subagent_type", "")
                        prompt = "%s %s" % (tool_input.get("description", ""),
                                            tool_input.get("prompt", ""))
                        if subagent in EDITING_SUBAGENTS:
                            last_edit_idx = idx
                            unknown_edit = True
                        elif matches_verify(prompt):
                            candidates.append((idx, block.get("id")))
                elif btype == "tool_result":
                    is_error = bool(block.get("is_error"))
                    results[block.get("tool_use_id")] = (
                        is_error, result_text(block.get("content")))

    if last_edit_idx == -1:
        allow()
    if not unknown_edit and edited_paths and all(
            p.endswith(DOC_SUFFIXES) for p in edited_paths):
        allow()
    for cand_idx, tool_use_id in candidates:
        if cand_idx > last_edit_idx and not result_failed(results.get(tool_use_id)):
            allow()

    print(json.dumps({"decision": "block", "reason": NUDGE}))
    sys.exit(0)


if __name__ == "__main__":
    main()
