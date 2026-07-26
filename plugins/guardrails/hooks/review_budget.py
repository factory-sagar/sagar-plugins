#!/usr/bin/env python3
"""Bound reviewer fan-out per user request.

Reviewer stage and role binding remain workflow prose guidance; they are not enforced here.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Mapping

from guardrails_log import log_decision

STATE_VERSION = 3
REVIEWERS = {"change-review", "security", "review-worker"}
CHANGE_REVIEW_CAP = 6
SECURITY_CAP = 4
REVIEW_WORKER_CAP = 6
COMBINED_REVIEWER_CAP = 12
REVIEWER_CAPS = {
    "change-review": CHANGE_REVIEW_CAP,
    "security": SECURITY_CAP,
    "review-worker": REVIEW_WORKER_CAP,
}


def state_directory() -> Path:
    configured = os.environ.get("DROID_REVIEW_BUDGET_DIR")
    return Path(configured) if configured else Path(tempfile.gettempdir()) / "droid-review-budget"


def review_state_path(state_dir: Path, session_id: str) -> Path:
    safe_id = "".join(char for char in session_id if char.isalnum() or char in "-_")
    return state_dir / f"{safe_id or 'session'}.json"


def load_review_state(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("version") != STATE_VERSION:
        return None
    return payload


def write_review_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


@contextmanager
def locked_state(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def transcript_cursor(transcript_path: str) -> str:
    if not transcript_path:
        return ""
    transcript = Path(transcript_path).expanduser()
    try:
        lines = transcript.read_text(encoding="utf-8").splitlines()
    except OSError:
        return str(transcript)
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") == "message":
            message = record.get("message")
            if isinstance(message, dict) and message.get("hookEventName"):
                continue
        record_id = record.get("id")
        if record_id:
            return str(record_id)
    return str(transcript)


def request_token(prompt: str, transcript_path: str) -> str:
    raw = f"{transcript_cursor(transcript_path)}\0{prompt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def begin_request(
    *,
    state_dir: Path,
    session_id: str,
    prompt: str,
    transcript_path: str,
) -> Path:
    path = review_state_path(state_dir, session_id)
    token = request_token(prompt, transcript_path)
    with locked_state(path):
        existing = load_review_state(path)
        if existing is not None and existing.get("request_token") == token:
            return path
        write_review_state(
            path,
            {
                "version": STATE_VERSION,
                "session_id": session_id,
                "request_token": token,
                "calls_so_far": {},
            },
        )
    return path


def budget_violation(
    *,
    subagent_type: str,
    calls_so_far: Mapping[str, int],
) -> str | None:
    if subagent_type not in REVIEWERS:
        return None
    cap = REVIEWER_CAPS[subagent_type]
    if calls_so_far.get(subagent_type, 0) >= cap:
        return (
            f"The {subagent_type} reviewer cap of {cap} calls per user request was hit. "
            "A new user instruction resets the budget."
        )
    if sum(calls_so_far.get(reviewer, 0) for reviewer in REVIEWERS) >= COMBINED_REVIEWER_CAP:
        return (
            f"The combined reviewer cap of {COMBINED_REVIEWER_CAP} calls per user request "
            "was hit. A new user instruction resets the budget."
        )
    return None


def reserve_review_call(
    *,
    state_dir: Path,
    session_id: str,
    subagent_type: str,
) -> str | None:
    path = review_state_path(state_dir, session_id)
    with locked_state(path):
        state = load_review_state(path)
        if state is None:
            # A cost bound must not block legitimate review when its state is unavailable.
            log_decision(
                hook="review_budget",
                event="PreToolUse",
                decision="allow",
                session_id=session_id,
                detail="review budget state unavailable; allowing call",
            )
            return None
        calls_so_far = state.get("calls_so_far")
        if not isinstance(calls_so_far, dict) or not all(
            isinstance(name, str) and isinstance(count, int) and count >= 0
            for name, count in calls_so_far.items()
        ):
            log_decision(
                hook="review_budget",
                event="PreToolUse",
                decision="allow",
                session_id=session_id,
                detail="review budget counters unavailable; allowing call",
            )
            return None
        violation = budget_violation(
            subagent_type=subagent_type,
            calls_so_far=calls_so_far,
        )
        if violation is not None:
            return violation
        if subagent_type in REVIEWERS:
            calls_so_far[subagent_type] = calls_so_far.get(subagent_type, 0) + 1
            write_review_state(path, state)
    return None


def emit(output: dict[str, object]) -> None:
    print(json.dumps(output))


def deny(reason: str, session_id: str) -> None:
    log_decision(
        hook="review_budget",
        event="PreToolUse",
        decision="deny",
        session_id=session_id,
        detail=reason,
    )
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if not isinstance(hook_input, dict):
        return 0

    event = hook_input.get("hook_event_name")
    session_id = str(hook_input.get("session_id") or "session")
    if event == "UserPromptSubmit":
        begin_request(
            state_dir=state_directory(),
            session_id=session_id,
            prompt=str(hook_input.get("prompt") or ""),
            transcript_path=str(hook_input.get("transcript_path") or ""),
        )
        return 0

    if event != "PreToolUse" or hook_input.get("tool_name") != "Task":
        return 0
    tool_input = hook_input.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    subagent_type = tool_input.get("subagent_type")
    if not isinstance(subagent_type, str) or subagent_type not in REVIEWERS:
        return 0
    violation = reserve_review_call(
        state_dir=state_directory(),
        session_id=session_id,
        subagent_type=subagent_type,
    )
    if violation is not None:
        deny(violation, session_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
