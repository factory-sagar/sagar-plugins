#!/usr/bin/env python3
"""Warn when the installed guardrails plugin revision is behind its source."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from guardrails_log import log_decision
from pre_push_policy import default_branch

COMMIT_ISH = re.compile(r"^[0-9a-fA-F]{7,64}$")


def run(command: list[str], cwd: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def run_text(command: list[str], cwd: str) -> str | None:
    result = run(command, cwd)
    if result is None or result.returncode != 0:
        return None
    return result.stdout.strip() or None


def installed_revision(plugin_root: str | None) -> str | None:
    if not plugin_root:
        return None
    for part in reversed(Path(plugin_root).parts):
        if COMMIT_ISH.fullmatch(part):
            return part
    return None


def marketplace_name(plugin_root: str) -> str | None:
    parts = Path(plugin_root).parts
    for index, part in enumerate(parts):
        if COMMIT_ISH.fullmatch(part) and index >= 2:
            return parts[index - 2]
    return None


def source_revision(
    cwd: str,
    marketplace: str,
) -> tuple[str, str | None] | None:
    repo_root = run_text(["git", "rev-parse", "--show-toplevel"], cwd)
    if not repo_root or Path(repo_root).name != marketplace:
        return None
    branch = default_branch(repo_root)
    revision = (
        run_text(["git", "rev-parse", f"origin/{branch}"], repo_root)
        if branch
        else None
    )
    return repo_root, revision or run_text(["git", "rev-parse", "HEAD"], repo_root)


def is_ancestor(ancestor: str, descendant: str, repo_root: str) -> bool | None:
    result = run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        repo_root,
    )
    if result is None:
        return None
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    return None


def freshness_status(
    installed: str,
    source: str,
    repo_root: str,
) -> str:
    if installed == source:
        return "current"
    installed_is_ancestor = is_ancestor(installed, source, repo_root)
    if installed_is_ancestor is None:
        return "git-unavailable"
    if installed_is_ancestor:
        return "stale"
    source_is_ancestor = is_ancestor(source, installed, repo_root)
    if source_is_ancestor is None:
        return "git-unavailable"
    return "current" if source_is_ancestor else "unrelated-revisions"


def output(context: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                },
                "suppressOutput": True,
            }
        )
    )


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        log_decision(
            hook="plugin_freshness",
            event="SessionStart",
            decision="skip",
            session_id="session",
            detail="invalid hook input",
        )
        return 0

    session_id = str(hook_input.get("session_id") or "session")
    cwd = str(hook_input.get("cwd") or os.getcwd())
    plugin_root = os.environ.get("DROID_PLUGIN_ROOT")
    installed = installed_revision(plugin_root)
    marketplace = marketplace_name(plugin_root) if plugin_root else None
    if not installed or not marketplace:
        log_decision(
            hook="plugin_freshness",
            event="SessionStart",
            decision="skip",
            session_id=session_id,
            detail="installed revision unavailable",
        )
        return 0
    source = source_revision(cwd, marketplace)
    if source is None or source[1] is None:
        log_decision(
            hook="plugin_freshness",
            event="SessionStart",
            decision="skip",
            session_id=session_id,
            detail="source repository unavailable",
        )
        return 0
    repo_root, source_revision_value = source
    installed_revision_value = run_text(
        ["git", "rev-parse", "--verify", installed],
        repo_root,
    )
    if not installed_revision_value:
        log_decision(
            hook="plugin_freshness",
            event="SessionStart",
            decision="skip",
            session_id=session_id,
            detail="installed revision unavailable",
        )
        return 0
    status = freshness_status(installed_revision_value, source_revision_value, repo_root)
    if status != "stale":
        log_decision(
            hook="plugin_freshness",
            event="SessionStart",
            decision="skip",
            session_id=session_id,
            detail=status,
        )
        return 0

    context = (
        f"Plugin install is stale: {installed_revision_value[:7]} is behind "
        f"{source_revision_value[:7]}. "
        "Run `droid plugin update`."
    )
    log_decision(
        hook="plugin_freshness",
        event="SessionStart",
        decision="warn",
        session_id=session_id,
        detail=context,
    )
    output(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
