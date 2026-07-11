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


def action_position(text: str, pattern: str) -> int | None:
    for match in re.finditer(pattern, text, re.IGNORECASE):
        boundary = max(
            text.rfind(".", 0, match.start()),
            text.rfind(";", 0, match.start()),
            text.rfind(" but ", 0, match.start()),
            text.rfind(" then ", 0, match.start()),
        )
        clause = text[boundary + 1 : match.start()]
        if re.search(r"\b(do not|don't|never|without)\b", clause, re.IGNORECASE):
            continue
        return match.start()
    return None


def route_intent(prompt: str) -> list[str] | None:
    text = " ".join(prompt.strip().split())
    if not text or INFORMATIONAL.search(text):
        return None
    review_match = re.search(
        r"\b(review|address)\b",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"\b(PR|pull request|branch|commit|comments?|threads?|diff|staged|change)\b",
        text,
        re.IGNORECASE,
    )
    review_position = (
        action_position(text, r"\b(review|address)\b")
        if review_match
        else None
    )
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
