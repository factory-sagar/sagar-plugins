#!/usr/bin/env python3
"""Enforce bounded change-review calls for each submitted user request."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

STATE_VERSION = 1
REVIEW_TAG = re.compile(
    r"^(\[review:(?:standard|deep:(?:primary|challenge)|"
    r"final:(\d+):(primary|challenge))\])(?:\s|$)"
)
FINAL_HEAD_HINT = re.compile(
    r"\b(?:final|frozen|current)\b.{0,48}\b(?:head|branch|diff)\b",
    re.IGNORECASE,
)
ROUND_ONE_SLOTS = {
    "[review:final:1:primary]",
    "[review:final:1:challenge]",
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
                "final_slots": [],
            },
        )
    return path


def review_task_violation(
    description: str,
    *,
    state: dict[str, object],
    prompt: str = "",
) -> str | None:
    match = REVIEW_TAG.match(description)
    if match is None:
        return (
            "Every change-review Task description must start with a review stage tag: "
            "`[review:standard]`, `[review:deep:primary|challenge]`, or "
            "`[review:final:<1|2>:primary|challenge]`."
        )

    tag = match.group(1)
    round_text = match.group(2)
    if round_text is None:
        if FINAL_HEAD_HINT.search(f"{description}\n{prompt}"):
            return (
                "A frozen/current/final head, branch, or diff review must use a "
                "final-head tag so the "
                "two-round correction budget can be enforced."
            )
        return None

    round_number = int(round_text)
    if round_number not in {1, 2}:
        return (
            "The final-head gate may run at most two rounds per user request. "
            "Stop as blocked and request a new user decision."
        )

    raw_slots = state.get("final_slots")
    slots = set(raw_slots) if isinstance(raw_slots, list) else set()
    if tag in slots:
        return f"Review budget slot {tag} was already used for this user request."
    if round_number == 2 and not ROUND_ONE_SLOTS.issubset(slots):
        return "Complete round 1 primary and challenge reviews before starting round 2."
    return None


def reserve_review_call(
    *,
    state_dir: Path,
    session_id: str,
    description: str,
    prompt: str = "",
) -> str | None:
    path = review_state_path(state_dir, session_id)
    with locked_state(path):
        state = load_review_state(path)
        if state is None:
            return (
                "Review budget state is unavailable for this user request. "
                "Stop and ask the user to resubmit the review request."
            )
        violation = review_task_violation(description, state=state, prompt=prompt)
        if violation is not None:
            return violation
        match = REVIEW_TAG.match(description)
        if match is not None and match.group(2) is not None:
            raw_slots = state.get("final_slots")
            slots = list(raw_slots) if isinstance(raw_slots, list) else []
            slots.append(match.group(1))
            state["final_slots"] = slots
            write_review_state(path, state)
    return None


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
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
        print(json.dumps({"suppressOutput": True}))
        return 0

    if event != "PreToolUse" or hook_input.get("tool_name") != "Task":
        return 0
    tool_input = hook_input.get("tool_input") or {}
    if tool_input.get("subagent_type") != "change-review":
        return 0
    violation = reserve_review_call(
        state_dir=state_directory(),
        session_id=session_id,
        description=str(tool_input.get("description") or ""),
        prompt=str(tool_input.get("prompt") or ""),
    )
    if violation is not None:
        deny(violation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
