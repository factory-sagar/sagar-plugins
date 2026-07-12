#!/usr/bin/env python3
"""Inject the canonical four-workflow route for intuitive user prompts."""

from __future__ import annotations

import json
import re
import sys

INFORMATIONAL = re.compile(
    r"^\s*(what (?:does|is|are)|how does|why does|explain|describe|define)\b",
    re.IGNORECASE,
)
CLAUSE_SEPARATORS = (".", ";", " but ", " then ")


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
        if (
            match.group(1).lower() == "review"
            and re.search(r"\b(?:every|a|an|the)\s*$", clause, re.IGNORECASE)
        ):
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
    if not text or INFORMATIONAL.search(text):
        return None
    if re.match(
        r"^(?:should|would)\s+(?:i|we|you)\s+approve\s+and\s+(?:merge|land)\b",
        text,
        re.IGNORECASE,
    ):
        return None
    review_target_match = re.search(
        r"\b(PR|pull request|branch|commit|comments?|threads?|diff|staged|change)\b",
        text,
        re.IGNORECASE,
    )
    review_position = review_or_address_position(text) if review_target_match else None
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
    implement_position = action_position(text, r"\b(implement|build|apply)\b")
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
    ship_position = action_position(
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


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    routes = route_intent(str(hook_input.get("prompt") or ""))
    if routes is None:
        return 0
    route_text = " → ".join(f"`{route}`" for route in routes)
    context = (
        f"Canonical workflow route: {route_text}. Invoke these primary workflows in order. "
        "The user's wording controls authority and outcome; each workflow selects its internal "
        "policy skills and droids. Do not invoke competing top-level workflows."
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
