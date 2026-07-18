"""Append-only decision log shared by every guardrail hook.

Hooks write to stdout only to change agent behavior; everything worth
auditing (injections, denies, blocks, forced stops) is appended here as one
JSON line so noise complaints become reproducible test inputs instead of
feelings. Logging must never break a hook, so every failure is swallowed.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path


def log_directory() -> Path:
    configured = os.environ.get("DROID_GUARDRAILS_LOG_DIR")
    return Path(configured) if configured else Path(tempfile.gettempdir()) / "droid-guardrails"


def log_decision(
    *,
    hook: str,
    event: str,
    decision: str,
    session_id: str,
    detail: str,
) -> None:
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hook": hook,
        "event": event,
        "decision": decision,
        "session_id": session_id,
        "detail": detail,
    }
    try:
        directory = log_directory()
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "decisions.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(record, sort_keys=True)}\n")
    except OSError:
        pass
