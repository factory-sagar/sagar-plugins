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

from guardrails_log import log_decision

STATE_VERSION = 2
MAX_LOOP_PASSES = 3
REVIEW_TAG = re.compile(
    r"^(\[review:(?:standard(?::(?:retry(?::security)?|security))?|"
    r"deep:(?:discovery|primary|challenge|resume|security|retry:(?:primary|challenge|security))|"
    r"pair:(?:primary|challenge|security|retry:(?:primary|challenge|security))|"
    r"loop:(\d+)(?::(retry(?::security)?|security))?)\])(?:\s|$)"
)
SELECTED_SECURITY = re.compile(r"\[security:selected\]")
STANDARD_SLOTS = {
    "[review:standard]",
    "[review:standard:retry]",
    "[review:standard:security]",
    "[review:standard:retry:security]",
}
DEEP_SLOTS = {
    "[review:deep:discovery]",
    "[review:deep:primary]",
    "[review:deep:challenge]",
    "[review:deep:resume]",
    "[review:deep:security]",
    "[review:deep:retry:primary]",
    "[review:deep:retry:challenge]",
    "[review:deep:retry:security]",
}
DEEP_WORKER_SLOTS = {
    "[review:deep:discovery]",
    "[review:deep:primary]",
    "[review:deep:challenge]",
    "[review:deep:resume]",
    "[review:deep:retry:primary]",
    "[review:deep:retry:challenge]",
}
PAIR_SLOTS = {
    "[review:pair:primary]",
    "[review:pair:challenge]",
    "[review:pair:security]",
    "[review:pair:retry:primary]",
    "[review:pair:retry:challenge]",
    "[review:pair:retry:security]",
}
PAIR_CORE_SLOTS = {
    "[review:pair:primary]",
    "[review:pair:challenge]",
}
CHANGE_REVIEW_STANDARD_SLOTS = {
    "[review:standard]",
    "[review:standard:retry]",
}
CHANGE_REVIEW_PAIR_SLOTS = {
    "[review:pair:primary]",
    "[review:pair:challenge]",
    "[review:pair:retry:primary]",
    "[review:pair:retry:challenge]",
}
RETRY_PREREQUISITES = {
    "[review:deep:retry:primary]": "[review:deep:primary]",
    "[review:deep:retry:challenge]": "[review:deep:challenge]",
    "[review:pair:retry:primary]": "[review:pair:primary]",
    "[review:pair:retry:challenge]": "[review:pair:challenge]",
}
SECURITY_RETRY_PREREQUISITES = {
    "[review:standard:retry:security]": "[review:standard:security]",
    "[review:deep:retry:security]": "[review:deep:security]",
    "[review:pair:retry:security]": "[review:pair:security]",
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
                "review_family": None,
                "review_slots": [],
            },
        )
    return path


def review_family(tag: str) -> str | None:
    if tag in STANDARD_SLOTS:
        return "standard"
    if tag in DEEP_SLOTS:
        return "deep"
    if tag in PAIR_SLOTS:
        return "pair"
    return None


def review_slots(state: dict[str, object]) -> set[str]:
    raw_slots = state.get("review_slots")
    if isinstance(raw_slots, list):
        return {slot for slot in raw_slots if isinstance(slot, str)}
    return set()


def reserved_family(state: dict[str, object], slots: set[str]) -> str | None:
    family = state.get("review_family")
    if isinstance(family, str):
        return family
    for slot in slots:
        slot_family = review_family(slot)
        if slot_family is not None:
            return slot_family
    return None


def loop_budget_violation() -> str:
    return (
        f"The review-fix loop allows at most {MAX_LOOP_PASSES} delta verification "
        "passes per user request. Report the remaining findings as blocked and ask "
        "the user for a new decision; a new user instruction resets the loop budget."
    )


def review_task_violation(
    description: str,
    *,
    state: dict[str, object],
    prompt: str = "",
    resume: object = None,
) -> str | None:
    match = REVIEW_TAG.match(description)
    if match is None:
        return (
            "Every change-review Task description must start with a review stage tag: "
            "`[review:standard]`, `[review:standard:retry|security|retry:security]`, "
            "`[review:deep:discovery|primary|challenge|resume|security|retry:...]`, "
            "`[review:pair:primary|challenge|security|retry:...]`, or "
            "`[review:loop:<n>]` with optional `:retry`, `:security`, or "
            "`:retry:security` variants."
        )

    tag = match.group(1)
    loop_round = match.group(2)
    slots = review_slots(state)
    existing_family = reserved_family(state, slots)

    if loop_round is not None:
        if existing_family is None:
            return (
                "Run the initial review stage (standard, deep, or pair) before a "
                "delta verification pass."
            )
        if existing_family == "pair" and not PAIR_CORE_SLOTS.issubset(slots):
            return (
                "Complete the pair primary and challenge reviews before the "
                "delta verification loop."
            )
        iteration = int(loop_round)
        if iteration < 1 or iteration > MAX_LOOP_PASSES:
            return loop_budget_violation()
        variant = match.group(3)
        if variant == "retry":
            base = f"[review:loop:{iteration}]"
            if base not in slots:
                return (
                    f"Complete the review {base} before using the {tag} "
                    "evidence-completion retry slot."
                )
        elif variant == "retry:security":
            base = f"[review:loop:{iteration}:security]"
            if base not in slots:
                return (
                    f"Complete the review {base} before using the {tag} "
                    "evidence-completion retry slot."
                )
        elif variant == "security":
            base = f"[review:loop:{iteration}]"
            if base not in slots:
                return (
                    f"Reserve the delta verification pass {base} before its "
                    "security pass."
                )
        elif iteration > 1 and f"[review:loop:{iteration - 1}]" not in slots:
            return (
                f"Complete delta verification pass {iteration - 1} before "
                f"pass {iteration}."
            )
        if tag in slots:
            return f"Review budget slot {tag} was already used for this user request."
        return None

    family = review_family(tag)
    if existing_family is not None and existing_family != family:
        return (
            f"Review budget is already reserved for the {existing_family} family; "
            f"do not start a {family} review in the same user request."
        )
    if tag == "[review:deep:resume]":
        if "[review:deep:primary]" not in slots:
            return (
                "Reserve the deep primary review stage before resuming the "
                "review-worker Task."
            )
        if not isinstance(resume, str) or not resume.strip():
            return (
                "A deep review-worker resume Task must provide a nonempty "
                "`tool_input.resume` target."
            )
        return None
    if tag in slots:
        return f"Review budget slot {tag} was already used for this user request."
    if tag == "[review:standard:retry]" and "[review:standard]" not in slots:
        return (
            "Complete the standard review before using the "
            "`[review:standard:retry]` slot."
        )
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
    resume: object = None,
) -> str | None:
    path = review_state_path(state_dir, session_id)
    with locked_state(path):
        state = load_review_state(path)
        if state is None:
            return (
                "Review budget state is unavailable for this user request. "
                "Stop and ask the user to resubmit the review request."
            )
        violation = review_task_violation(
            description,
            state=state,
            prompt=prompt,
            resume=resume,
        )
        if violation is not None:
            return violation
        match = REVIEW_TAG.match(description)
        if match is not None:
            tag = match.group(1)
            if tag != "[review:deep:resume]":
                raw_slots = state.get("review_slots")
                slots = list(raw_slots) if isinstance(raw_slots, list) else []
                slots.append(tag)
                state["review_slots"] = slots
                family = review_family(tag)
                if family is not None:
                    state["review_family"] = family
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
    tool_input = hook_input.get("tool_input") or {}
    subagent_type = tool_input.get("subagent_type")
    description = str(tool_input.get("description") or "")
    match = REVIEW_TAG.match(description)
    if subagent_type not in {"change-review", "review-worker", "security"}:
        return 0
    if subagent_type == "review-worker":
        if match is None:
            deny("Every review-worker Task must start with a deep review stage tag.", session_id)
            return 0
        if match.group(1) not in DEEP_WORKER_SLOTS:
            deny(
                "A review-worker Task may use only deep discovery, primary, challenge, "
                "resume, or their prerequisite retry review stage tags.",
                session_id,
            )
            return 0
    if subagent_type == "security" and match is None:
        deny("Every security Task must start with a `:security` review stage tag.", session_id)
        return 0
    if match is not None:
        tag = match.group(1)
        is_security_tag = tag.endswith(":security]")
        if (
            subagent_type == "security"
            and is_security_tag
            and SELECTED_SECURITY.search(description) is None
        ):
            human_description = description[match.end() :].lstrip()
            description = f"{tag} [security:selected]"
            if human_description:
                description = f"{description} {human_description}"
            normalized = True
        else:
            normalized = False
        if subagent_type == "security" and not is_security_tag:
            deny("A security Task may use only `:security` review stage tags.", session_id)
            return 0
        if subagent_type == "change-review" and is_security_tag:
            deny("A change-review Task may not use `:security` review stage tags.", session_id)
            return 0
        if subagent_type == "change-review" and (
            tag not in CHANGE_REVIEW_STANDARD_SLOTS
            and tag not in CHANGE_REVIEW_PAIR_SLOTS
            and not tag.startswith("[review:loop:")
        ):
            deny(
                "A change-review Task may use only standard, pair, or delta-loop "
                "review stage tags.",
                session_id,
            )
            return 0
    else:
        normalized = False
    violation = reserve_review_call(
        state_dir=state_directory(),
        session_id=session_id,
        description=description,
        prompt=str(tool_input.get("prompt") or ""),
        resume=tool_input.get("resume"),
    )
    if violation is not None:
        deny(violation, session_id)
    elif normalized:
        log_decision(
            hook="review_budget",
            event="PreToolUse",
            decision="normalize",
            session_id=session_id,
            detail="inserted selected security marker",
        )
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "updatedInput": {"description": description},
                },
                "suppressOutput": True,
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
