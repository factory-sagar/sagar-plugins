---
name: resolve-pr-comments
version: 1.0.0
description: |
  Fetch all review comments on a pull request, apply fixes for each one, verify, and push.
  Handles bot comments (factory-droid, code-review bots) and human reviewer comments alike.
  Parses ```suggestion blocks, prose feedback, and P0/P1/P2 severity tags.
  Use when:
  - The user says "fix droid comments", "resolve PR comments", "address review feedback"
  - The user provides a PR URL and wants comments addressed
  - The user says "fix the review comments on <PR>"
  - The user wants to batch-apply code review suggestions from a PR
---

# Resolve PR Comments

Given a PR URL or number, fetch all review comments, apply fixes for each, run verification, and push.

## Inputs

- **PR URL or number** (required): e.g. `https://github.com/<owner>/<repo>/pull/250` or `#250`

## Workflow

### 1. Fetch the PR and Extract Comments

Use `FetchUrl` on the PR URL to get:
- PR metadata (title, branch, base, state)
- File changes (diffs)
- All review comments (inline and general)

The FetchUrl output may be truncated. If so, read the artifact file to get the full content. Search for `User:` or `Comment` markers to find each comment block.

Parse each comment to categorize it:
- **Code suggestion**: Contains a ```suggestion block with replacement code. Apply directly or adapt to surrounding code.
- **Prose feedback**: Describes a problem without inline code. Understand the intent and implement a fix.
- **Severity tags**: P0/P1/P2 or similar prefixes indicate priority. Address P0/P1 first.
- **Bot vs human**: Bot comments (factory-droid, vercel, etc.) often include structured suggestions. Human comments may be more open-ended.

Skip comments that are:
- Already resolved (have a reply indicating the fix was applied)
- Purely informational with no action needed (e.g. deployment status from vercel[bot])
- Acknowledgments or "nice catch" replies

### 2. Check Out the PR Branch

```bash
git fetch origin <branch-name>
git checkout <branch-name>
```

If the branch is already checked out in a worktree, work in that worktree directory instead:
```bash
git worktree list
```

### 3. Apply Fixes

For each actionable comment:

1. Read the file and surrounding code referenced by the comment
2. If the comment includes a ```suggestion block, apply the suggested code (adapting to match existing style and formatting)
3. If the comment is prose feedback, understand the issue and implement the fix
4. Read the file again after editing to confirm the change is correct

Group related comments that touch the same file. Apply all changes to a file before moving to the next.

If a comment is a false positive or the suggestion would break existing behavior, note it and skip. Do not apply changes you believe are incorrect.

### 4. Format and Verify

Run the project's format, lint, typecheck, and test commands. Discover them by reading `package.json`, `Makefile`, `pyproject.toml`, or the CI config.

If formatting changes the applied code (e.g. prettier rewrites), let it. Re-read the formatted file to confirm the fix is still correct.

If any check fails, fix the failure before proceeding. Do not push broken code.

### 5. Commit and Push

```bash
git add -A
git commit -m "fix: address PR review comments

<summary of each fix, one bullet per comment>

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>"
```

If the commit message contains special characters (quotes, backticks), use `git commit -F -` with a heredoc to avoid shell escaping issues.

```bash
git push origin <branch-name>
```

### 6. Report

Summarize what was done:
- How many comments were found and how many were actionable
- What was fixed (one line per fix)
- What was skipped and why
- Confirm verification passed and changes are pushed

## What Not to Do

- Do not reply to comments on GitHub. The user can do that manually if needed.
- Do not rebase or restructure the PR. Only apply the fixes requested by comments.
- Do not add tests unless a comment explicitly asks for them.
- Do not push if any verification check fails.
- Do not apply suggestions that would introduce bugs or break existing behavior. Skip and note instead.
