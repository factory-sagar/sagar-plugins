#!/usr/bin/env python3
"""Run UserPromptSubmit guardrails in their established emission order."""

from __future__ import annotations

import io
import sys

import intent_router
import review_budget


def main() -> int:
    hook_input = sys.stdin.read()
    status = 0
    original_stdin = sys.stdin
    try:
        for hook in (intent_router, review_budget):
            sys.stdin = io.StringIO(hook_input)
            result = hook.main()
            if status == 0 and result != 0:
                status = result
    finally:
        sys.stdin = original_stdin
    return status


if __name__ == "__main__":
    raise SystemExit(main())
