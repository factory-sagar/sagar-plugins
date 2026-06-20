---
description: Fix a PR end-to-end - reason about comments, fix bugs, reply, resolve, wait for CI, approve
disable-model-invocation: true
---

Fix the pull request: $ARGUMENTS

Use the fix-pr skill to:
1. Fetch the PR and extract all review comments
2. Check out the PR branch
3. Triage each comment - reason about whether it is a real bug, valid improvement, style nit, false positive, or question
4. Fix the valid bugs and improvements
5. Run format, lint, typecheck, and tests
6. Commit and push
7. Reply to every comment on GitHub and resolve the threads
8. Wait for CI to go green
9. Approve the PR if it is not your own, or say "done" if it is

If no PR URL or number is provided, ask the user for one.
