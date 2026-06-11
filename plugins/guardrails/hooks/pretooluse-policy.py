#!/usr/bin/env python3
"""PreToolUse guardrail for Execute: deny catastrophic commands, escalate
destructive ones to an explicit user confirmation.

Runs independently of the session autonomy level, so even at auto-high a
matched command is denied or downgraded to "ask". Set GUARDRAILS_DISABLE=1
to bypass.
"""
import json
import os
import re
import sys


def emit(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


# Matches only at command position (start of string, after a shell separator,
# or after command substitution), so command names quoted inside strings such
# as `echo "rm -rf /"` do not trigger rules.
CMD = r"(?:^|[;&|(]|\$\(|`)\s*(?:sudo\s+)?"


def rm_rf_targets(command):
    """Targets of any rm invocation carrying both recursive and force flags."""
    targets = []
    for m in re.finditer(CMD + r"rm\s+((?:-{1,2}[^\s]+\s+)*)([^|;&]*)", command):
        flags = m.group(1)
        short = "".join(re.findall(r"(?<!-)-([A-Za-z]+)", flags))
        recursive = "r" in short or "R" in short or "--recursive" in flags
        force = "f" in short or "--force" in flags
        if recursive and force:
            targets.extend(t for t in m.group(2).split() if not t.startswith("-"))
    return targets


def is_catastrophic_target(target):
    home = os.path.expanduser("~")
    t = target.strip("'\"").replace("${HOME}", home).replace("$HOME", home)
    if t in ("/", "/*", "~", "~/", "~/*"):
        return True
    norm = os.path.normpath(os.path.expanduser(t))
    return norm in ("/", "/*", home, home + "/*")


DENY_RULES = [
    (CMD + r"git\s+push\b(?=[^|;&]*(\s--force(-with-lease)?\b|\s-f\b))"
           r"(?=[^|;&]*\b(origin|upstream)\b)(?=[^|;&]*\b(main|master)\b)",
     "Force push to main/master rewrites shared history. Blocked by guardrails."),
    (r"\bsudo\s+rm\b[^|;&]*-\w*r",
     "Recursive rm with sudo can destroy system files. Blocked by guardrails."),
    (CMD + r"mkfs(\.\w+)?\b",
     "Filesystem format command. Blocked by guardrails."),
    (CMD + r"dd\b[^|;&]*\bof=/dev/",
     "Raw write to a device node. Blocked by guardrails."),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
     "Fork bomb. Blocked by guardrails."),
    (CMD + r"chmod\b(?=[^|;&]*\s-R\b|[^|;&]*\s--recursive\b)"
           r"(?=[^|;&]*\b0?777\b)[^|;&]*\s/+(\s|$)",
     "Recursive chmod 777 on /. Blocked by guardrails."),
]

ASK_RULES = [
    (CMD + r"git\s+reset\s+--hard\b",
     "git reset --hard irreversibly discards uncommitted changes."),
    (CMD + r"git\s+clean\b[^|;&]*(-[A-Za-z]*f|--force)",
     "git clean deletes untracked files, which may be unsaved work."),
    (CMD + r"git\s+checkout\s+(--\s+)?\.(\s|$)",
     "Broad git checkout discards all unstaged changes."),
    (CMD + r"git\s+restore\b(?![^|;&]*--staged)[^|;&]*\s\.(\s|$)",
     "Broad git restore discards all unstaged changes."),
    (CMD + r"git\s+push\b[^|;&]*(\s--force\b(?!-)|\s-f\b)",
     "Force push rewrites remote history."),
    (CMD + r"git\s+stash\s+(drop|clear)\b",
     "Dropping stashes irreversibly deletes stashed work."),
    (CMD + r"git\s+branch\s+-D\b",
     "Force-deleting a branch can lose unmerged commits."),
    (CMD + r"find\b[^|;&]*\s-delete\b",
     "find -delete removes files matching a pattern; results can be surprising."),
]


def main():
    if os.environ.get("GUARDRAILS_DISABLE"):
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("tool_name") != "Execute":
        sys.exit(0)
    command = (data.get("tool_input") or {}).get("command") or ""
    if not command:
        sys.exit(0)

    targets = rm_rf_targets(command)
    if any(is_catastrophic_target(t) for t in targets):
        emit("deny", "Recursive force delete of / or the home directory. Blocked by guardrails.")
    for pattern, reason in DENY_RULES:
        if re.search(pattern, command):
            emit("deny", reason)
    if targets:
        emit("ask", "Recursive force delete (rm -rf). Confirm the target is correct and contains no untracked work.")
    for pattern, reason in ASK_RULES:
        if re.search(pattern, command):
            emit("ask", reason + " Confirm to proceed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
