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
    r"^(\[review:(?:standard(?::(?:retry(?::security)?|security))?|"
    r"deep:(?:primary|challenge|security|retry:(?:primary|challenge|security))|"
    r"final:(\d+):(?:primary|challenge|security|retry:(?:primary|challenge|security)))\])(?:\s|$)"
)
SELECTED_SECURITY = re.compile(r"\[security:selected\]")
FINAL_HEAD_HINT = re.compile(
    r"\b(?:final|frozen|current)\b.{0,48}\b(?:head|branch|diff)\b",
    re.IGNORECASE,
)
ROUND_ONE_SLOTS = {
    "[review:final:1:primary]",
    "[review:final:1:challenge]",
}
ROUND_TWO_TERMINAL_SLOTS = {
    "[review:final:2:primary]",
    "[review:final:2:challenge]",
}
STANDARD_SLOTS = {
    "[review:standard]",
    "[review:standard:retry]",
    "[review:standard:security]",
    "[review:standard:retry:security]",
}
DEEP_SLOTS = {
    "[review:deep:primary]",
    "[review:deep:challenge]",
    "[review:deep:security]",
    "[review:deep:retry:primary]",
    "[review:deep:retry:challenge]",
    "[review:deep:retry:security]",
}
RETRY_PREREQUISITES = {
    "[review:deep:retry:primary]": "[review:deep:primary]",
    "[review:deep:retry:challenge]": "[review:deep:challenge]",
    "[review:final:1:retry:primary]": "[review:final:1:primary]",
    "[review:final:1:retry:challenge]": "[review:final:1:challenge]",
}
SECURITY_RETRY_PREREQUISITES = {
    "[review:standard:retry:security]": "[review:standard:security]",
    "[review:deep:retry:security]": "[review:deep:security]",
    "[review:final:1:retry:security]": "[review:final:1:security]",
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
                "review_family": None,
                "review_slots": [],
            },
        )
    return path


def review_family(tag: str) -> str:
    if tag in STANDARD_SLOTS:
        return "standard"
    if tag in DEEP_SLOTS:
        return "deep"
    return "final"


def review_slots(state: dict[str, object]) -> set[str]:
    raw_slots = state.get("review_slots")
    if isinstance(raw_slots, list):
        return {slot for slot in raw_slots if isinstance(slot, str)}
    raw_final_slots = state.get("final_slots")
    if isinstance(raw_final_slots, list):
        return {slot for slot in raw_final_slots if isinstance(slot, str)}
    return set()


def reserved_family(state: dict[str, object], slots: set[str]) -> str | None:
    family = state.get("review_family")
    if isinstance(family, str):
        return family
    for slot in slots:
        if slot in STANDARD_SLOTS or slot in DEEP_SLOTS or slot.startswith(
            "[review:final:"
        ):
            return review_family(slot)
    return None


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
            "`[review:standard]`, `[review:standard:retry|security|retry:security]`, "
            "`[review:deep:primary|challenge|security|retry:security]`, or "
            "`[review:final:<1|2>:primary|challenge|security|retry:security]`."
        )

    tag = match.group(1)
    round_text = match.group(2)
    slots = review_slots(state)
    if tag.startswith("[review:final:1:") and any(
        slot.startswith("[review:final:2:") for slot in slots
    ):
        return (
            "Final round 2 has already started; do not reserve any further "
            "final round 1 review stages."
        )
    selected_round_two_security = (
        tag == "[review:final:2:security]" and SELECTED_SECURITY.search(description)
    )
    if ROUND_TWO_TERMINAL_SLOTS.issubset(slots) and not selected_round_two_security:
        return (
            "The final-head gate may run at most two rounds per user request. "
            "Stop as blocked and request a new user decision."
        )

    family = review_family(tag)
    existing_family = reserved_family(state, slots)
    if existing_family is not None and existing_family != family:
        return (
            f"Review budget is already reserved for the {existing_family} family; "
            f"do not start a {family} review in the same user request."
        )
    if tag in slots:
        return f"Review budget slot {tag} was already used for this user request."

    if round_text is None:
        if FINAL_HEAD_HINT.search(f"{description}\n{prompt}"):
            return (
                "A frozen/current/final head, branch, or diff review must use a "
                "final-head tag so the "
                "two-round correction budget can be enforced."
            )
        if tag == "[review:standard:retry]" and "[review:standard]" not in slots:
            return (
                "Complete the standard review before using the "
                "`[review:standard:retry]` slot."
            )
        prerequisite = RETRY_PREREQUISITES.get(tag) or SECURITY_RETRY_PREREQUISITES.get(
            tag
        )
        if prerequisite is not None and prerequisite not in slots:
            return (
                f"Complete the review {prerequisite} before using the {tag} "
                "evidence-completion retry slot."
            )
        return None

    round_number = int(round_text)
    if round_number not in {1, 2}:
        return (
            "The final-head gate may run at most two rounds per user request. "
            "Stop as blocked and request a new user decision."
        )
    if round_number == 2 and not ROUND_ONE_SLOTS.issubset(slots):
        return "Complete round 1 primary and challenge reviews before starting round 2."
    if round_number == 2 and tag.startswith("[review:final:2:retry:"):
        return "Final round 2 is decision-only and does not allow evidence retries."
    prerequisite = RETRY_PREREQUISITES.get(tag) or SECURITY_RETRY_PREREQUISITES.get(tag)
    if prerequisite is not None and prerequisite not in slots:
        return (
            f"Complete the review {prerequisite} before using the {tag} "
            "evidence-completion retry slot."
        )
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
        if match is not None:
            tag = match.group(1)
            raw_slots = state.get("review_slots")
            if not isinstance(raw_slots, list):
                raw_final_slots = state.get("final_slots")
                raw_slots = list(raw_final_slots) if isinstance(raw_final_slots, list) else []
            raw_slots.append(tag)
            state["review_slots"] = raw_slots
            state["review_family"] = review_family(tag)

        if match is not None and match.group(2) is not None:
            raw_slots = state.get("final_slots")
            slots = list(raw_slots) if isinstance(raw_slots, list) else []
            slots.append(match.group(1))
            state["final_slots"] = slots
        if match is not None:
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
    subagent_type = tool_input.get("subagent_type")
    description = str(tool_input.get("description") or "")
    match = REVIEW_TAG.match(description)
    if subagent_type not in {"change-review", "security"}:
        return 0
    if subagent_type == "security" and match is None:
        deny("Every security Task must start with a `:security` review stage tag.")
        return 0
    if match is not None:
        tag = match.group(1)
        is_security_tag = tag.endswith(":security]")
        if (
            subagent_type == "security"
            and is_security_tag
            and SELECTED_SECURITY.search(description) is None
        ):
            deny(
                "Every budgeted security Task description must include "
                "`[security:selected]`."
            )
            return 0
        if subagent_type == "security" and not is_security_tag:
            deny("A security Task may use only `:security` review stage tags.")
            return 0
        if subagent_type == "change-review" and is_security_tag:
            deny("A change-review Task may not use `:security` review stage tags.")
            return 0
    violation = reserve_review_call(
        state_dir=state_directory(),
        session_id=session_id,
        description=description,
        prompt=str(tool_input.get("prompt") or ""),
    )
    if violation is not None:
        deny(violation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
