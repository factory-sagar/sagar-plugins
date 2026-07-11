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


def route_intent(prompt: str) -> list[str] | None:
    text = " ".join(prompt.strip().split())
    if not text or INFORMATIONAL.search(text):
        return None
    review = re.search(
        r"\b(review|address)\b",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"\b(PR|pull request|branch|commit|comments?|threads?|diff|staged|change)\b",
        text,
        re.IGNORECASE,
    )
    plan = re.search(
        r"\b(plan|spec|scope|design|architect(?:ure)?)\b",
        text,
        re.IGNORECASE,
    )
    implement = not re.search(
        r"\b(do not|don't|never|without)\s+(implement|build|apply)\b",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"\b(implement|build|apply)\b",
        text,
        re.IGNORECASE,
    )
    ship = not re.search(
        r"\b(do not|don't|never|without)\s+(ship|push|merge|land)\b",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"\b(ship|push|merge|land|merge-ready)\b",
        text,
        re.IGNORECASE,
    )

    routes: list[str] = []
    if review:
        routes.append("review-pr")
    else:
        if plan:
            routes.append("spec")
        if implement:
            routes.append("implement")
    if ship:
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
