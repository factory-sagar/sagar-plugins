#!/usr/bin/env python3
"""Block unsafe git push shapes before they reach the remote."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys

from delivery_ledger import default_branch, parse_push_command
from guardrails_log import log_decision

PIPEFAIL_PREFIX = re.compile(r"^\s*set\s+-o\s+pipefail\s*(?:;|&&)")


def targets_default_branch(push_args: list[str], default_branch: str) -> bool:
    positional = [arg for arg in push_args if not arg.startswith("-")]
    refspecs = positional[1:] if positional else []
    for raw in refspecs:
        refspec = raw.removeprefix("+")
        destination = refspec.split(":", 1)[-1]
        normalized = destination.removeprefix("refs/heads/")
        if normalized == default_branch:
            return True
    return False


def push_policy_violation(
    command: str,
    *,
    branch: str | None,
    default_branch: str | None,
) -> str | None:
    if parse_push_command(command) is None:
        return None
    if "--no-verify" in command:
        return "Push bypasses repository verification. Run the configured checks and push without --no-verify."
    if "|" in command and PIPEFAIL_PREFIX.search(command) is None:
        return (
            "Push output is piped without pipefail, which can hide a failed push. "
            "Start the command with `set -o pipefail;`."
        )
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    try:
        push_args = tokens[tokens.index("push") + 1 :]
    except ValueError:
        push_args = tokens
    if any(token in {"--force", "-f"} for token in push_args):
        return "Use --force-with-lease when rewritten history must be pushed."
    if branch and default_branch and branch == default_branch:
        return f"Direct push to default branch {default_branch!r} is blocked. Create a feature branch."
    if default_branch and targets_default_branch(push_args, default_branch):
        return f"Direct push to default branch {default_branch!r} is blocked. Create a feature branch."
    return None


def run(command: list[str], cwd: str) -> str | None:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def current_branch(cwd: str) -> str | None:
    return run(["git", "branch", "--show-current"], cwd)


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if hook_input.get("tool_name") != "Execute":
        return 0

    command = str((hook_input.get("tool_input") or {}).get("command", ""))
    cwd = str(hook_input.get("cwd") or os.getcwd())
    push_cwd = parse_push_command(command, cwd)
    if push_cwd is None:
        return 0

    violation = push_policy_violation(
        command,
        branch=current_branch(push_cwd),
        default_branch=default_branch(push_cwd),
    )
    if violation:
        log_decision(
            hook="pre_push_policy",
            event="PreToolUse",
            decision="deny",
            session_id=str(hook_input.get("session_id") or "session"),
            detail=violation,
        )
        print(violation, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
