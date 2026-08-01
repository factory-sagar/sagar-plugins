#!/usr/bin/env python3
"""Prevent a pushed session from claiming completion before delivery is closed.

Obligations are scoped to what this request actually authorized:

- Push integrity (clean worktree, remote holds the local head) always applies
  after a recorded push.
- PR obligations (PR head parity, CI, body stamp) apply only when an open PR
  exists for the pushed branch; a branch pushed without a PR is not a delivery.
- Unresolved review threads block only when this request granted approve or
  merge authority (both require zero open threads); otherwise threads are the
  agent's to report, not this gate's to block.
- The PR-body stamp is enforced only for bodies that already carry a
  `pr-body-head` marker; PRs managed outside this workflow are not blocked.
- A recorded push whose PR has merged closes delivery once local HEAD is
  contained in the remote default branch; squash merges move HEAD to the merge commit.
- When gh itself is unavailable the gate fails closed with one consolidated
  line instead of one line per unverifiable fact.
- A continuation that changes nothing ends the session with the remaining
  obligations instead of blocking forever: block reasons repeat at most once.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass

from delivery_ledger import (
    classify_delivery_host,
    clear_push_state,
    default_branch,
    load_state,
    locked_state,
    remote_host,
    state_directory,
    state_path,
)
from guardrails_log import log_decision
from intent_router import intent_state_directory, load_request_intent

BODY_HEAD_MARKER = "pr-body-head"
BODY_MARKER_PREFIX = f"<!-- {BODY_HEAD_MARKER}="

PR_STATE_OK = "ok"
PR_STATE_NONE = "none"
PR_STATE_UNAVAILABLE = "unavailable"

GH_UNAVAILABLE_OBLIGATION = (
    "Delivery gate could not verify PR, CI, or review-thread state via gh."
)
CI_RUNNING_OBLIGATION = "CI is still running for the current PR head."


def host_skip_note(host: str) -> str:
    return (
        f"Delivery gate: PR, CI, and review-thread verification is unsupported for "
        f"{host}; only git push integrity was checked."
    )


@dataclass(frozen=True, slots=True)
class DeliverySnapshot:
    local_head: str | None
    remote_head: str | None
    dirty_tracked: bool | None
    unexpected_untracked: tuple[str, ...] | None
    pr_state: str
    pr_head: str | None
    checks_complete: bool | None
    checks_green: bool | None
    unresolved_threads: int | None
    body_fresh: bool | None


def body_is_fresh(body: str, head: str) -> bool:
    return f"{BODY_MARKER_PREFIX}{head} -->" in body


def classify_worktree(
    status: str | None,
    baseline_untracked: list[str],
) -> tuple[bool | None, tuple[str, ...] | None]:
    if status is None:
        return None, None
    dirty_tracked = False
    current_untracked = set()
    for line in status.splitlines():
        if line.startswith("?? "):
            current_untracked.add(line[3:])
        elif line:
            dirty_tracked = True
    unexpected = tuple(sorted(current_untracked - set(baseline_untracked)))
    return dirty_tracked, unexpected


def pending_obligations(
    state: dict[str, object],
    snapshot: DeliverySnapshot,
    *,
    thread_authority: bool,
    delivery_host: str = "github",
) -> list[str]:
    pushed_head = str(state.get("pushed_head") or "")
    obligations: list[str] = []

    if snapshot.dirty_tracked is None:
        obligations.append("Delivery gate could not verify whether the worktree is clean.")
    elif snapshot.dirty_tracked:
        obligations.append("The worktree contains uncommitted tracked changes.")
    if snapshot.unexpected_untracked is None:
        obligations.append("Delivery gate could not verify untracked-file ownership.")
    elif snapshot.unexpected_untracked:
        paths = ", ".join(snapshot.unexpected_untracked[:3])
        obligations.append(f"New untracked delivery files remain: {paths}.")
    if snapshot.local_head and snapshot.local_head != pushed_head:
        obligations.append("Local HEAD contains unpushed work created after the recorded push.")
    if snapshot.remote_head is None:
        obligations.append("Delivery gate could not verify the remote branch HEAD.")
    elif snapshot.local_head and snapshot.remote_head != snapshot.local_head:
        obligations.append("Remote branch does not contain the current local HEAD.")

    if delivery_host != "github":
        return obligations
    if snapshot.pr_state == PR_STATE_UNAVAILABLE:
        obligations.append(GH_UNAVAILABLE_OBLIGATION)
    elif snapshot.pr_state == PR_STATE_OK:
        if snapshot.pr_head is None:
            obligations.append("Delivery gate could not verify the PR head.")
        elif snapshot.remote_head and snapshot.pr_head != snapshot.remote_head:
            obligations.append("The PR head does not match the pushed remote HEAD.")
        if snapshot.checks_complete is None or snapshot.checks_green is None:
            obligations.append("Delivery gate could not verify CI for the current PR head.")
        elif not snapshot.checks_complete:
            obligations.append(CI_RUNNING_OBLIGATION)
        elif not snapshot.checks_green:
            obligations.append("CI is not green for the current PR head.")
        if thread_authority:
            if snapshot.unresolved_threads is None:
                obligations.append("Delivery gate could not verify unresolved review threads.")
            elif snapshot.unresolved_threads:
                obligations.append(
                    f"{snapshot.unresolved_threads} unresolved review threads remain."
                )
        if snapshot.body_fresh is False:
            obligations.append("PR body is not stamped for the current PR head.")

    return obligations


def next_step(
    state: dict[str, object],
    obligations: list[str],
    *,
    delivery_host: str = "github",
) -> str:
    raw_pr_number = state.get("pr_number")
    pr_target = f" {raw_pr_number}" if isinstance(raw_pr_number, int) else ""
    if delivery_host == "github" and any(
        "could not verify" in item for item in obligations
    ):
        return "Next: run `gh auth status`, then retry delivery verification."
    if any(
        keyword in item
        for item in obligations
        for keyword in ("worktree", "untracked", "unpushed", "Remote branch")
    ):
        return (
            "Next: run `git status --porcelain`, commit or remove the listed work, "
            "and push the branch."
        )
    if CI_RUNNING_OBLIGATION in obligations:
        return (
            "Do not retry Stop or emit an interim final response while CI is "
            "pending. Run `gh pr checks"
            f"{pr_target} --watch --interval 10` in the foreground and wait for it "
            "to exit."
        )
    if any("CI is not green" in item for item in obligations):
        return f"Next: run `gh pr checks{pr_target}`, fix the failing check, and repush."
    if any("PR head does not match" in item for item in obligations):
        return "Next: run `git push` so the PR head matches the pushed branch."
    if any("review threads" in item for item in obligations):
        return (
            f"Next: resolve or answer every open review thread on the PR "
            f"(`gh pr view{pr_target} --comments`)."
        )
    return (
        "Next: regenerate the PR body for the current head and include "
        "`<!-- pr-body-head=<head-sha> -->`."
    )


def delivery_gate_output(
    state: dict[str, object],
    snapshot: DeliverySnapshot,
    *,
    stop_hook_active: bool,
    thread_authority: bool,
    delivery_host: str = "github",
) -> dict[str, object] | None:
    obligations = pending_obligations(
        state,
        snapshot,
        thread_authority=thread_authority,
        delivery_host=delivery_host,
    )
    if not obligations:
        return None

    if stop_hook_active and obligations == state.get("last_block_obligations"):
        return {
            "continue": False,
            "stopReason": (
                "Delivery gate: unchanged obligations after a continuation: "
                + "; ".join(obligations)
                + " Resolve them, then finish delivery in a new turn."
            ),
        }
    if stop_hook_active and obligations == [CI_RUNNING_OBLIGATION]:
        raw_pr_number = state.get("pr_number")
        pr_target = f" {raw_pr_number}" if isinstance(raw_pr_number, int) else ""
        return {
            "continue": False,
            "stopReason": (
                "Delivery is still waiting for CI and this turn is not accepted as "
                "complete. Run `gh pr checks"
                f"{pr_target} --watch --interval 10` in the foreground and resume "
                "only after it exits."
            ),
        }

    reason = (
        "Delivery remains incomplete: "
        + "; ".join(obligations)
        + "\n"
        + next_step(state, obligations, delivery_host=delivery_host)
    )
    return {"decision": "block", "reason": reason}


def run(
    command: list[str],
    cwd: str,
    timeout: int = 8,
) -> subprocess.CompletedProcess[str] | None:
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


def merged_delivery_closed(state: dict[str, object], repo_root: str) -> bool:
    pr_number = state.get("pr_number")
    if not isinstance(pr_number, int):
        return False
    pr_state = run_text(
        ["gh", "pr", "view", str(pr_number), "--json", "state", "--jq", ".state"],
        repo_root,
    )
    if pr_state is None or pr_state.upper() != "MERGED":
        return False
    default = default_branch(repo_root)
    if not default:
        return False
    result = run(
        ["git", "merge-base", "--is-ancestor", "HEAD", f"origin/{default}"],
        repo_root,
    )
    return result is not None and result.returncode == 0


def detect_delivery_host(repo_root: str) -> tuple[str, str]:
    remote_url = run_text(["git", "remote", "get-url", "origin"], repo_root)
    if remote_url is None:
        remote_url = run_text(
            ["git", "config", "--get", "remote.origin.url"],
            repo_root,
        )
    host = remote_host(remote_url)
    if host is None:
        return "none", "no origin remote"
    enterprise_hosts = set()
    if host != "github.com":
        result = run(["gh", "auth", "status", "--hostname", host], repo_root)
        if result is not None and result.returncode == 0:
            enterprise_hosts.add(host)
    return classify_delivery_host(remote_url, enterprise_hosts), host


def fetch_pr(
    repo_root: str,
    pr_number: int | None,
) -> tuple[dict[str, object] | None, str]:
    """Fetch the PR for the pushed branch, classifying why it is missing.

    Only messages that positively identify a missing PR map to "none";
    every other failure (auth, network, timeout, parse) is "unavailable"
    so verification failures cannot silently skip PR obligations.
    """
    command = ["gh", "pr", "view"]
    if pr_number:
        command.append(str(pr_number))
    command.extend(["--json", "number,headRefOid,body"])
    result = run(command, repo_root)
    if result is None:
        return None, PR_STATE_UNAVAILABLE
    if result.returncode != 0:
        stderr = (result.stderr or "").lower()
        if "no pull requests found" in stderr or "could not resolve to a pullrequest" in stderr:
            return None, PR_STATE_NONE
        return None, PR_STATE_UNAVAILABLE
    try:
        value = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return None, PR_STATE_UNAVAILABLE
    if not isinstance(value, dict):
        return None, PR_STATE_UNAVAILABLE
    return value, PR_STATE_OK


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


def snapshot_delivery(
    state: dict[str, object],
    *,
    thread_authority: bool,
    delivery_host: str = "github",
) -> tuple[DeliverySnapshot, int | None]:
    repo_root = str(state.get("repo_root") or "")
    branch = str(state.get("branch") or "")
    raw_pr_number = state.get("pr_number")
    pr_number = raw_pr_number if isinstance(raw_pr_number, int) else None

    local_head = run_text(["git", "rev-parse", "HEAD"], repo_root)
    remote_head = run_text(["git", "rev-parse", f"origin/{branch}"], repo_root)
    status = run_text(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        repo_root,
    )
    baseline_untracked = state.get("baseline_untracked")
    dirty_tracked, unexpected_untracked = classify_worktree(
        status,
        baseline_untracked if isinstance(baseline_untracked, list) else [],
    )

    pr: dict[str, object] | None = None
    pr_state = PR_STATE_NONE
    pr_head: str | None = None
    checks_complete: bool | None = None
    checks_green: bool | None = None
    unresolved_threads: int | None = None
    body_fresh: bool | None = None
    if delivery_host == "github":
        pr, pr_state = fetch_pr(repo_root, pr_number)
    if pr_state == PR_STATE_OK and pr is not None:
        if isinstance(pr.get("number"), int):
            pr_number = int(pr["number"])
        pr_head = str(pr["headRefOid"]) if pr.get("headRefOid") else None
        body = str(pr.get("body") or "")
        if pr_number is not None:
            checks_complete, checks_green = fetch_checks(repo_root, pr_number)
            if thread_authority:
                unresolved_threads = fetch_unresolved_threads(repo_root, pr_number)
        if pr_head and BODY_MARKER_PREFIX in body:
            body_fresh = body_is_fresh(body, pr_head)

    snapshot = DeliverySnapshot(
        local_head=local_head,
        remote_head=remote_head,
        dirty_tracked=dirty_tracked,
        unexpected_untracked=unexpected_untracked,
        pr_state=pr_state,
        pr_head=pr_head,
        checks_complete=checks_complete,
        checks_green=checks_green,
        unresolved_threads=unresolved_threads,
        body_fresh=body_fresh,
    )
    return snapshot, pr_number


def record_last_block(path, obligations: list[str]) -> None:
    with locked_state(path):
        current = load_state(path)
        if current is None:
            return
        current["last_block_obligations"] = obligations
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(current, sort_keys=True), encoding="utf-8")
        temporary.replace(path)


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    session_id = str(hook_input.get("session_id") or "session")
    cwd = str(hook_input.get("cwd") or "")
    repo_root = run_text(["git", "rev-parse", "--show-toplevel"], cwd)
    if not repo_root:
        return 0
    path = state_path(state_directory(), session_id, repo_root)
    state = load_state(path)
    if state is None:
        return 0
    if not state.get("pushed_head"):
        return 0
    if merged_delivery_closed(state, repo_root):
        clear_push_state(path, state)
        return 0

    intent = load_request_intent(intent_state_directory(), session_id)
    thread_authority = bool(intent and intent.get("merge_or_approve"))
    delivery_host, host_name = detect_delivery_host(repo_root)
    snapshot, pr_number = snapshot_delivery(
        state,
        thread_authority=thread_authority,
        delivery_host=delivery_host,
    )
    gate_state = {**state, "pr_number": pr_number}
    output = delivery_gate_output(
        gate_state,
        snapshot,
        stop_hook_active=bool(hook_input.get("stop_hook_active")),
        thread_authority=thread_authority,
        delivery_host=delivery_host,
    )
    if delivery_host != "github":
        log_decision(
            hook="stop_delivery_gate",
            event="Stop",
            decision="skip",
            session_id=session_id,
            detail=host_skip_note(host_name),
        )
    if output is None:
        clear_push_state(path, state)
        return 0

    obligations = pending_obligations(
        gate_state,
        snapshot,
        thread_authority=thread_authority,
        delivery_host=delivery_host,
    )
    record_last_block(path, obligations)
    log_decision(
        hook="stop_delivery_gate",
        event="Stop",
        decision="block" if output.get("decision") == "block" else "stop",
        session_id=session_id,
        detail="; ".join(obligations),
    )
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
