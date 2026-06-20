---
description: Resolve all review comments on a PR (apply suggestions, verify, push)
disable-model-invocation: true
---

Resolve all review comments on the pull request: $ARGUMENTS

Use the resolve-pr-comments skill to:
1. Fetch the PR and extract all review comments
2. Check out the PR branch
3. Apply fixes for each actionable comment
4. Run format, lint, typecheck, and tests
5. Commit and push

If no PR URL or number is provided, ask the user for one.
