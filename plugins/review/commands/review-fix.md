---
description: Review a change end-to-end then fix it - read-only review, apply fixes, verify, commit locally, ask before push
disable-model-invocation: true
---

Review and fix the change: $ARGUMENTS

Use the review-fix skill to:
1. Resolve the scope and load the diff (PR URL, branch, commit range, or staged changes)
2. Choose the tier - light by default, deep (exhaustive multi-pass) for large or risky diffs, confirming before escalating
3. Run the read-only review (change-review / security droids for light; convention discovery + resumed multi-pass review for deep)
4. Consolidate and triage findings
5. Fix the actionable findings in code
6. Run format, lint, typecheck, and tests
7. Commit locally - do NOT push
8. Summarize, then ask whether to push

If no review target is provided, ask the user for one.
