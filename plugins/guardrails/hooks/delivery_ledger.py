#!/usr/bin/env python3
"""Record successful git pushes for deterministic delivery completion checks."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

STATE_VERSION = 2
SHELL_SEPARATORS = {"&&", ";", "||", "|"}


def remote_host(remote_url: str | None) -> str | None:
    if not remote_url:
        return None
    value = remote_url.strip()
    if not value:
        return None
    if "://" in value:
        authority = value.split("://", 1)[1].split("/", 1)[0]
        host = authority.rsplit("@", 1)[-1].split(":", 1)[0]
    else:
        host = value.rsplit("@", 1)[-1].split(":", 1)[0]
    return host.lower() or None


def classify_delivery_host(
    remote_url: str | None,
    github_enterprise_hosts: set[str] | None = None,
) -> str:
    host = remote_host(remote_url)
    if host is None:
        return "none"
    if host == "github.com" or host in (github_enterprise_hosts or set()):
        return "github"
    return "unsupported"


def parse_push_command(command: str, fallback_cwd: str = ".") -> str | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None

    effective_cwd = Path(fallback_cwd)
    start = 0
    for index in range(len(tokens) + 1):
        if index < len(tokens) and tokens[index] not in SHELL_SEPARATORS:
            continue
        segment = tokens[start:index]
        separator = tokens[index] if index < len(tokens) else None
        start = index + 1
        if not segment:
            continue
        if segment[0] == "cd" and len(segment) == 2:
            candidate = Path(segment[1]).expanduser()
            effective_cwd = candidate if candidate.is_absolute() else effective_cwd / candidate
            if separator in {"&&", ";"}:
                continue

        try:
            git_index = segment.index("git")
        except ValueError:
            continue

        args = segment[git_index + 1 :]
        git_cwd = effective_cwd
        cursor = 0
        while cursor < len(args):
            arg = args[cursor]
            if arg in {"-C", "-c", "--git-dir", "--work-tree"}:
                if cursor + 1 >= len(args):
                    break
                if arg == "-C":
                    candidate = Path(args[cursor + 1]).expanduser()
                    git_cwd = candidate if candidate.is_absolute() else git_cwd / candidate
                cursor += 2
                continue
            if arg.startswith("-C") and len(arg) > 2:
                candidate = Path(arg[2:]).expanduser()
                git_cwd = candidate if candidate.is_absolute() else git_cwd / candidate
                cursor += 1
                continue
            if arg.startswith("-"):
                cursor += 1
                continue
            if arg == "push":
                return str(git_cwd.resolve())
            break
    return None


def is_push_command(command: str) -> bool:
    return parse_push_command(command) is not None


def state_directory() -> Path:
    configured = os.environ.get("DROID_DELIVERY_LEDGER_DIR")
    return Path(configured) if configured else Path(tempfile.gettempdir()) / "droid-delivery-ledger"


def state_path(state_dir: Path, session_id: str, repo_root: str | None = None) -> Path:
    safe_id = "".join(char for char in session_id if char.isalnum() or char in "-_")
    repo_id = (
        hashlib.sha256(repo_root.encode("utf-8")).hexdigest()[:12]
        if repo_root
        else "no-repo"
    )
    return state_dir / f"{safe_id or 'session'}-{repo_id}.json"


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


def record_push(
    *,
    state_dir: Path,
    session_id: str,
    repo_root: str,
    branch: str,
    pushed_head: str,
    pr_number: int | None,
    baseline_untracked: list[str] | None = None,
) -> Path:
    path = state_path(state_dir, session_id, repo_root)
    with locked_state(path):
        existing = load_state(path) or {}
        existing_baseline = (
            existing.get("baseline_untracked")
            if existing.get("repo_root") == repo_root
            else None
        )
        preserved_baseline = (
            existing_baseline
            if isinstance(existing_baseline, list)
            else baseline_untracked or []
        )
        payload = {
            "version": STATE_VERSION,
            "session_id": session_id,
            "repo_root": repo_root,
            "branch": branch,
            "pushed_head": pushed_head,
            "pr_number": pr_number,
            "baseline_untracked": sorted(set(preserved_baseline)),
        }
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        temporary.replace(path)
    return path


def record_session_baseline(
    *,
    state_dir: Path,
    session_id: str,
    repo_root: str,
    baseline_untracked: list[str],
) -> Path:
    path = state_path(state_dir, session_id, repo_root)
    with locked_state(path):
        existing = load_state(path)
        if (
            existing is not None
            and existing.get("session_id") == session_id
            and existing.get("repo_root") == repo_root
        ):
            return path
        payload = {
            "version": STATE_VERSION,
            "session_id": session_id,
            "repo_root": repo_root,
            "branch": None,
            "pushed_head": None,
            "pr_number": None,
            "baseline_untracked": sorted(set(baseline_untracked)),
        }
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        temporary.replace(path)
    return path


def load_state(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("version") != STATE_VERSION:
        return None
    return payload


def clear_push_state(path: Path, state: dict[str, object]) -> None:
    with locked_state(path):
        current = load_state(path) or state
        if current.get("pushed_head") != state.get("pushed_head"):
            return
        payload = {
            "version": STATE_VERSION,
            "session_id": current.get("session_id"),
            "repo_root": current.get("repo_root"),
            "branch": None,
            "pushed_head": None,
            "pr_number": None,
            "baseline_untracked": current.get("baseline_untracked", []),
        }
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        temporary.replace(path)


def run(command: list[str], cwd: str) -> str | None:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def resolve_push_state(cwd: str) -> tuple[str, str, str, int | None, list[str]] | None:
    repo_root = run(["git", "rev-parse", "--show-toplevel"], cwd)
    branch = run(["git", "branch", "--show-current"], cwd)
    head = run(["git", "rev-parse", "HEAD"], cwd)
    if not repo_root or not branch or not head:
        return None

    raw_pr = run(["gh", "pr", "view", "--json", "number", "--jq", ".number"], repo_root)
    try:
        pr_number = int(raw_pr) if raw_pr else None
    except ValueError:
        pr_number = None
    raw_untracked = run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        repo_root,
    )
    baseline_untracked = raw_untracked.splitlines() if raw_untracked else []
    return repo_root, branch, head, pr_number, baseline_untracked


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    event = hook_input.get("hook_event_name")
    cwd = str(hook_input.get("cwd") or os.getcwd())
    session_id = str(hook_input.get("session_id") or "session")
    if event == "SessionStart":
        repo_root = run(["git", "rev-parse", "--show-toplevel"], cwd)
        if not repo_root:
            return 0
        raw_untracked = run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            repo_root,
        )
        record_session_baseline(
            state_dir=state_directory(),
            session_id=session_id,
            repo_root=repo_root,
            baseline_untracked=raw_untracked.splitlines() if raw_untracked else [],
        )
        return 0

    if hook_input.get("tool_name") != "Execute":
        return 0
    command = str((hook_input.get("tool_input") or {}).get("command", ""))
    push_cwd = parse_push_command(command, cwd)
    if push_cwd is None:
        return 0

    tool_response = hook_input.get("tool_response")
    if isinstance(tool_response, dict) and tool_response.get("success") is False:
        return 0

    resolved = resolve_push_state(push_cwd)
    if resolved is None:
        return 0
    repo_root, branch, head, pr_number, baseline_untracked = resolved
    record_push(
        state_dir=state_directory(),
        session_id=session_id,
        repo_root=repo_root,
        branch=branch,
        pushed_head=head,
        pr_number=pr_number,
        baseline_untracked=baseline_untracked,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
