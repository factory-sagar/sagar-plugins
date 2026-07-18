#!/usr/bin/env python3
"""Inject the canonical four-workflow route for intuitive user prompts.

Precision over recall: a wrong or unnecessary injection is workflow noise, so
verbs fire only in imperative positions, questions and negations never route,
and `build`/`apply`/`address` additionally require an object that names real
workflow material. Every injection is recorded in the guardrails decision log,
and every prompt records this request's routes and merge/approve authority for
the stop-time delivery gate.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

from guardrails_log import log_decision

INFORMATIONAL = re.compile(
    r"^\s*(what(?:'s| does| is| are)|how (?:do|does|can|should|would)|why\b|"
    r"which\b|who\b|explain|describe|define|summarize|tell me)",
    re.IGNORECASE,
)
# "Should/would I|we|you ..." asks for advice; advice never routes a workflow
# and never grants authority.
ADVICE_QUESTION = re.compile(
    r"^(?:should|would)\s+(?:i|we|you)\b",
    re.IGNORECASE,
)
CLAUSE_SEPARATORS = (".", ";", " but ", " then ")
REVIEW_TARGET = re.compile(
    r"\b(PR|pull request|branch|commit|comments?|threads?|diff|staged|change)\b",
    re.IGNORECASE,
)
# "address" routes only toward review artifacts; addressing a root cause,
# a field, or a failing test is not a review request.
ADDRESS_TARGET = re.compile(
    r"\b(PR|pull request|comments?|threads?|review)\b",
    re.IGNORECASE,
)
# "build"/"apply" are common conversational verbs; they route to implement
# only when their object names workflow material.
IMPLEMENT_OBJECT = re.compile(
    r"\b(?:units?|plans?|specs?|fix(?:es)?|patch(?:es)?|diff|change ?sets?|"
    r"changes?|endpoints?|features?|approved)\b",
    re.IGNORECASE,
)
EXPLICIT_INVOCATION = (
    r"\b(?:use|run|invoke|with|via)\s+(?:the\s+)?`?{route}`?\b"
)

INTENT_STATE_VERSION = 1


def preceding_clause(text: str, end: int) -> str:
    separator_start: int | None = None
    separator_length = 0
    for separator in CLAUSE_SEPARATORS:
        position = text.rfind(separator, 0, end)
        if position >= 0 and (separator_start is None or position > separator_start):
            separator_start = position
            separator_length = len(separator)
    if separator_start is None:
        return text[:end]
    return text[separator_start + separator_length : end]


def following_window(text: str, start: int, width: int = 64) -> str:
    window = text[start : start + width]
    cut = len(window)
    for separator in CLAUSE_SEPARATORS:
        position = window.find(separator)
        if 0 <= position < cut:
            cut = position
    return window[:cut]


def action_position(text: str, pattern: str) -> int | None:
    for match in re.finditer(pattern, text, re.IGNORECASE):
        clause = preceding_clause(text, match.start())
        if re.search(r"\b(do not|don't|never|without)\b", clause, re.IGNORECASE):
            continue
        if (
            match.group().lower() == "merge"
            and re.search(r"\bblock\s*$", clause, re.IGNORECASE)
        ):
            continue
        return match.start()
    return None


def objected_action_position(text: str, pattern: str, target: re.Pattern[str]) -> int | None:
    for match in re.finditer(pattern, text, re.IGNORECASE):
        clause = preceding_clause(text, match.start())
        if re.search(r"\b(do not|don't|never|without)\b", clause, re.IGNORECASE):
            continue
        if target.search(following_window(text, match.end())):
            return match.start()
    return None


def shipping_position(text: str, pattern: str) -> int | None:
    """Imperative position for ship-family verbs, skipping noun usage.

    "The push failed", "merge conflicts", and "our last merge" describe
    events; only verb-position ship words route or grant authority.
    """
    for match in re.finditer(pattern, text, re.IGNORECASE):
        clause = preceding_clause(text, match.start())
        if re.search(r"\b(do not|don't|never|without)\b", clause, re.IGNORECASE):
            continue
        word = match.group(1).lower()
        if word == "merge" and re.search(r"\bblock\s*$", clause, re.IGNORECASE):
            continue
        if re.search(
            r"\b(?:the|a|an|this|that|my|our|your|its|their|failed|last|previous|every|each)\s*$",
            clause,
            re.IGNORECASE,
        ):
            continue
        if word == "merge" and re.match(
            r"\s+(?:conflicts?|commits?)\b",
            text[match.end():],
            re.IGNORECASE,
        ):
            continue
        return match.start()
    return None


def approval_position(text: str) -> int | None:
    for match in re.finditer(
        r"\bapprove(?:\s+and\s+(?:merge|land))?\s+(?:(?:the|this)\s+)?(?:PR|pull request)\b",
        text,
        re.IGNORECASE,
    ):
        clause = preceding_clause(text, match.start())
        if re.search(r"\b(do not|don't|never)\b", clause, re.IGNORECASE):
            continue
        prefix = " ".join(clause.strip().lower().split())
        if prefix not in {
            "",
            "please",
            "kindly",
            "can you",
            "could you",
            "will you",
            "can you please",
            "could you please",
            "will you please",
        }:
            continue
        return match.start()
    return None


def review_or_address_position(text: str) -> int | None:
    for match in re.finditer(r"\b(review|address)\b", text, re.IGNORECASE):
        clause = preceding_clause(text, match.start())
        if re.search(r"\b(do not|don't|never|without)\b", clause, re.IGNORECASE):
            continue
        verb = match.group(1).lower()
        if verb == "review":
            if re.search(r"\b(?:every|a|an|the)\s*$", clause, re.IGNORECASE):
                continue
            if not REVIEW_TARGET.search(text):
                continue
        else:
            if not ADDRESS_TARGET.search(text):
                continue
        return match.start()
    return None


def fix_review_comments_position(text: str) -> int | None:
    for match in re.finditer(
        r"\bfix\s+(?:every\s+)?review\s+comments?\b",
        text,
        re.IGNORECASE,
    ):
        clause = preceding_clause(text, match.start())
        if re.search(r"\b(do not|don't|never|without)\b", clause, re.IGNORECASE):
            continue
        return match.start()
    return None


def route_intent(prompt: str) -> list[str] | None:
    text = " ".join(prompt.strip().split())
    if not text or INFORMATIONAL.search(text) or ADVICE_QUESTION.match(text):
        return None
    review_position = review_or_address_position(text)
    fix_comments_position = fix_review_comments_position(text)
    if fix_comments_position is not None and (
        review_position is None or fix_comments_position < review_position
    ):
        review_position = fix_comments_position
    approved_pr_position = approval_position(text)
    if approved_pr_position is not None and (
        review_position is None or approved_pr_position < review_position
    ):
        review_position = approved_pr_position
    plan_position = action_position(
        text,
        r"\b(plan|spec|scope|design|architect(?:ure)?)\b",
    )
    implement_candidates = [
        position
        for position in (
            action_position(text, r"\bimplement\b"),
            objected_action_position(text, r"\b(?:build|apply)\b", IMPLEMENT_OBJECT),
        )
        if position is not None
    ]
    implement_position = min(implement_candidates) if implement_candidates else None
    if implement_position is None and re.search(
        r"\bexecute\b.{0,40}\b(plan|program|unit|work package|change set)\b",
        text,
        re.IGNORECASE,
    ):
        implement_position = action_position(text, r"\bexecute\b")
    if implement_position is not None and re.search(
        r"\bapproved (plan|program|spec)\b",
        text,
        re.IGNORECASE,
    ):
        plan_position = None
    ship_position = shipping_position(
        text,
        r"\b(ship|push|merge|land|merge-ready)\b",
    )
    if re.search(
        r"\bapprove(?:\s+and\s+(?:merge|land))?\s+(?:the\s+)?plan\b",
        text,
        re.IGNORECASE,
    ):
        ship_position = None

    routes: list[str] = []
    if plan_position is not None:
        routes.append("spec")
    if (
        implement_position is not None
        and (review_position is None or implement_position < review_position)
    ):
        routes.append("implement")
    if review_position is not None:
        routes.append("review-pr")
    if ship_position is not None:
        routes.append("ship")
    return routes or None


def request_grants_merge_or_approve(prompt: str) -> bool:
    """Whether this request grants approve or merge authority.

    Both actions require zero unresolved review threads, so the stop-time
    delivery gate blocks on open threads only when this returns True.
    """
    text = " ".join(prompt.strip().split())
    if not text or INFORMATIONAL.search(text) or ADVICE_QUESTION.match(text):
        return False
    if re.search(
        r"\bapprove(?:\s+and\s+(?:merge|land))?\s+(?:the\s+)?plan\b",
        text,
        re.IGNORECASE,
    ):
        return False
    if approval_position(text) is not None:
        return True
    # "merge-ready" asks to prepare for a merge, not to merge.
    return shipping_position(text, r"\b(merge|land)\b(?!-ready)") is not None


def explicitly_invoked(prompt: str, routes: list[str]) -> bool:
    if len(routes) != 1:
        return False
    text = " ".join(prompt.strip().split())
    pattern = EXPLICIT_INVOCATION.format(route=re.escape(routes[0]))
    return re.search(pattern, text, re.IGNORECASE) is not None


def intent_state_directory() -> Path:
    configured = os.environ.get("DROID_INTENT_STATE_DIR")
    return Path(configured) if configured else Path(tempfile.gettempdir()) / "droid-intent-router"


def intent_state_path(state_dir: Path, session_id: str) -> Path:
    safe_id = "".join(char for char in session_id if char.isalnum() or char in "-_")
    return state_dir / f"{safe_id or 'session'}.json"


def record_request_intent(
    *,
    state_dir: Path,
    session_id: str,
    routes: list[str],
    merge_or_approve: bool,
) -> Path:
    path = intent_state_path(state_dir, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": INTENT_STATE_VERSION,
        "session_id": session_id,
        "routes": routes,
        "merge_or_approve": merge_or_approve,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
    return path


def load_request_intent(state_dir: Path, session_id: str) -> dict[str, object] | None:
    try:
        payload = json.loads(
            intent_state_path(state_dir, session_id).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("version") != INTENT_STATE_VERSION:
        return None
    return payload


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    prompt = str(hook_input.get("prompt") or "")
    session_id = str(hook_input.get("session_id") or "session")
    routes = route_intent(prompt)
    record_request_intent(
        state_dir=intent_state_directory(),
        session_id=session_id,
        routes=routes or [],
        merge_or_approve=request_grants_merge_or_approve(prompt),
    )
    if routes is None:
        return 0
    if explicitly_invoked(prompt, routes):
        return 0
    route_text = " → ".join(f"`{route}`" for route in routes)
    context = (
        f"Canonical workflow route: {route_text}. Invoke these primary workflows in order. "
        "The user's wording controls authority and outcome; each workflow selects its internal "
        "policy skills and droids. Do not invoke competing top-level workflows."
    )
    log_decision(
        hook="intent_router",
        event="UserPromptSubmit",
        decision="inject",
        session_id=session_id,
        detail=" -> ".join(routes),
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                },
                "suppressOutput": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
