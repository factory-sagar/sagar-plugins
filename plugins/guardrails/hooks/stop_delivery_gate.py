#!/usr/bin/env python3
"""Prevent a pushed session from claiming completion before delivery is closed."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass

from delivery_ledger import load_state, state_directory, state_path


@dataclass(frozen=True, slots=True)
class DeliverySnapshot:
    local_head: str | None
    remote_head: str | None
    pr_head: str | None
    dirty_worktree: bool | None
    checks_complete: bool | None
    checks_green: bool | None
    unresolved_threads: int | None
    body_fresh: bool | None


def pending_obligations(
    state: dict[str, object],
    snapshot: DeliverySnapshot,
) -> list[str]:
    pushed_head = str(state.get("pushed_head") or "")
    obligations: list[str] = []

    if snapshot.dirty_worktree is None:
        obligations.append("Delivery gate could not verify whether the worktree is clean.")
    elif snapshot.dirty_worktree:
        obligations.append("The worktree contains uncommitted or untracked changes.")
    if snapshot.local_head and snapshot.local_head != pushed_head:
        obligations.append("Local HEAD contains unpushed work created after the recorded push.")
    if snapshot.remote_head is None:
        obligations.append("Delivery gate could not verify the remote branch HEAD.")
    elif snapshot.local_head and snapshot.remote_head != snapshot.local_head:
        obligations.append("Remote branch does not contain the current local HEAD.")

    if snapshot.pr_head is None:
        obligations.append("Delivery gate could not verify an open PR for the pushed branch.")
    elif snapshot.remote_head and snapshot.pr_head != snapshot.remote_head:
        obligations.append("The PR head does not match the pushed remote HEAD.")

    if snapshot.checks_complete is None or snapshot.checks_green is None:
        obligations.append("Delivery gate could not verify CI for the current PR head.")
    elif not snapshot.checks_complete:
        obligations.append("CI is still running for the current PR head.")
    elif not snapshot.checks_green:
        obligations.append("CI is not green for the current PR head.")

    if snapshot.unresolved_threads is None:
        obligations.append("Delivery gate could not verify unresolved review threads.")
    elif snapshot.unresolved_threads:
        obligations.append(
            f"{snapshot.unresolved_threads} unresolved review threads remain."
        )

    if snapshot.body_fresh is None:
        obligations.append("Delivery gate could not verify PR body freshness.")
    elif not snapshot.body_fresh:
        obligations.append("PR body is not stamped for the current PR head.")

    return obligations


def run(command: list[str], cwd: str, timeout: int = 20) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def run_text(command: list[str], cwd: str) -> str | None:
    result = run(command, cwd)
    if result is None or result.returncode != 0:
        return None
    return result.stdout.strip()


def run_json(command: list[str], cwd: str) -> object | None:
    raw = run_text(command, cwd)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def fetch_pr(repo_root: str, pr_number: int | None) -> dict[str, object] | None:
    target = str(pr_number) if pr_number else None
    command = ["gh", "pr", "view"]
    if target:
        command.append(target)
    command.extend(["--json", "number,headRefOid,body"])
    value = run_json(command, repo_root)
    return value if isinstance(value, dict) else None


def fetch_checks(repo_root: str, pr_number: int) -> tuple[bool, bool] | tuple[None, None]:
    value = run_json(
        ["gh", "pr", "checks", str(pr_number), "--json", "name,state"],
        repo_root,
    )
    if not isinstance(value, list):
        return None, None
    states = {
        str(item.get("state", "")).upper()
        for item in value
        if isinstance(item, dict)
    }
    pending = {"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED"}
    failures = {"FAILURE", "FAILED", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"}
    return not bool(states & pending), not bool(states & (pending | failures))


def fetch_unresolved_threads(repo_root: str, pr_number: int) -> int | None:
    identity = run_json(["gh", "repo", "view", "--json", "nameWithOwner"], repo_root)
    if not isinstance(identity, dict):
        return None
    name_with_owner = str(identity.get("nameWithOwner") or "")
    if "/" not in name_with_owner:
        return None
    owner, name = name_with_owner.split("/", 1)
    query = """
query($owner:String!, $name:String!, $number:Int!, $endCursor:String) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$number) {
      reviewThreads(first:100, after:$endCursor) {
        nodes { isResolved }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""
    value = run_json(
        [
            "gh",
            "api",
            "graphql",
            "--paginate",
            "--slurp",
            "-f",
            f"query={query}",
            "-f",
            f"owner={owner}",
            "-f",
            f"name={name}",
            "-F",
            f"number={pr_number}",
        ],
        repo_root,
    )
    pages = value if isinstance(value, list) else [value]
    nodes = []
    for page in pages:
        try:
            nodes.extend(
                page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
            )
        except (KeyError, TypeError):
            return None
    return sum(
        1
        for node in nodes
        if isinstance(node, dict) and not bool(node.get("isResolved"))
    )


def snapshot_delivery(state: dict[str, object]) -> DeliverySnapshot:
    repo_root = str(state.get("repo_root") or "")
    branch = str(state.get("branch") or "")
    raw_pr_number = state.get("pr_number")
    pr_number = raw_pr_number if isinstance(raw_pr_number, int) else None

    local_head = run_text(["git", "rev-parse", "HEAD"], repo_root)
    remote_head = run_text(["git", "rev-parse", f"origin/{branch}"], repo_root)
    status = run_text(["git", "status", "--porcelain"], repo_root)
    pr = fetch_pr(repo_root, pr_number)
    if pr is not None and isinstance(pr.get("number"), int):
        pr_number = int(pr["number"])
    pr_head = str(pr.get("headRefOid")) if pr and pr.get("headRefOid") else None
    body = str(pr.get("body") or "") if pr else ""

    checks_complete: bool | None = None
    checks_green: bool | None = None
    unresolved_threads: int | None = None
    body_fresh: bool | None = None
    if pr_number is not None:
        checks_complete, checks_green = fetch_checks(repo_root, pr_number)
        unresolved_threads = fetch_unresolved_threads(repo_root, pr_number)
        body_fresh = bool(pr_head and f"<!-- sagar-plugins:head={pr_head} -->" in body)

    return DeliverySnapshot(
        local_head=local_head,
        remote_head=remote_head,
        pr_head=pr_head,
        dirty_worktree=None if status is None else bool(status),
        checks_complete=checks_complete,
        checks_green=checks_green,
        unresolved_threads=unresolved_threads,
        body_fresh=body_fresh,
    )


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    session_id = str(hook_input.get("session_id") or "session")
    path = state_path(state_directory(), session_id)
    state = load_state(path)
    if state is None:
        return 0

    obligations = pending_obligations(state, snapshot_delivery(state))
    if not obligations:
        path.unlink(missing_ok=True)
        return 0

    message = "Delivery remains incomplete:\n" + "\n".join(
        f"- {item}" for item in obligations
    )
    print(json.dumps({"decision": "block", "reason": message}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
