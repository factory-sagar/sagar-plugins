---
name: fix-pr
version: 2.1.0
description: |
  End-to-end PR fix workflow: fetch a PR, read every review comment, reason about whether
  each one is a real bug, fix the valid ones, reply to every comment, resolve the threads,
  push, wait for CI to go green, then approve the PR (or say "done" if it is your own).
  Handles bot comments (factory-droid, code-review bots) and human reviewer comments alike.
  Parses ```suggestion blocks, prose feedback, and P0/P1/P2 severity tags.
  Use when:
  - The user says "fix this PR", "fix droid comments", "resolve PR comments", "address review feedback"
  - The user provides a PR URL and wants comments addressed end-to-end
  - The user says "fix the review comments on <PR>" and expects CI + approval handled
  - The user wants to batch-apply code review suggestions from a PR and close the loop
---

# Fix PR

Given a PR URL or number, fetch all review comments, reason about each one, fix the valid
bugs, reply to every comment, resolve the threads, push, wait for CI, then approve the PR
(or say "done" if the PR is authored by factory-droid[bot]).

## Inputs

- **PR URL or number** (required): e.g. `https://github.com/<owner>/<repo>/pull/250` or `#250`

## Workflow

### 1. Fetch the PR and Extract Comments

Use `gh` to pull structured PR data. The JSON output gives you metadata, comments, and
reviews in one call:

```bash
gh pr view <url> --json number,title,author,headRefName,baseRefName,state,body,reviews,comments
```

Capture these fields:
- **author.login** - needed later to decide approve vs. done
- **headRefName** - the branch to check out
- **baseRefName** - the target branch (for context)
- **reviews** and **comments** - the full comment set

If `gh` is not available or returns insufficient data, fall back to `FetchUrl` on the PR
URL. The FetchUrl output may be truncated; if so, read the artifact file for the full
content and search for `User:` or `Comment` markers.

#### If the PR fixes a specific bug

Before reviewing comments, confirm the fix still addresses the real problem. Read the linked
issue / error report and the root cause. PRs go stale: the underlying bug may have already
been fixed by another merge into the base branch, making this PR a no-op or a conflict. If
so, surface that to the user before doing further work.

#### Comment sources to check

1. **Inline review comments** (line-level): these are the primary target. Pull them via:
   ```bash
   gh api repos/<owner>/<repo>/pulls/<number>/comments
   ```
2. **Review summaries** (general comments on each review): may contain actionable feedback.
3. **Issue comments** (PR-level conversation thread): usually informational, but check for
   reviewer requests.

For each comment, extract:
- Comment ID (needed for replies and resolving threads)
- Author (bot vs. human)
- File path and line number
- Body text (including ```suggestion blocks if present)
- Thread ID (for resolving; pull from `pull_request_review_id` or the thread endpoint)
- Whether the thread is already resolved

#### Comments to skip immediately

- Already resolved threads (have a reply indicating the fix was applied)
- Purely informational bot comments (e.g. deployment status from `vercel[bot]`, `github-actions[bot]`)
- Acknowledgments or "nice catch" replies
- CI status comments with no code feedback

### 2. Check Out the PR Branch

```bash
git fetch origin <branch-name>
git checkout <branch-name>
git pull origin <branch-name>
```

If the branch is already checked out in a worktree, work in that worktree directory instead:
```bash
git worktree list
```

Ensure the working tree is clean before making changes:
```bash
git status --porcelain
```

#### Bring the branch up to date (conditional)

Only rebase when the branch is **behind the base branch** or **CI is failing for
staleness-related reasons** (e.g. checks that pass on base but fail here). Do not rebase a
branch that is up to date and green: it rewrites history for no benefit.

Check how far behind the branch is:
```bash
git fetch origin <base-branch>
git rev-list --left-right --count origin/<base-branch>...HEAD
```
The first number is commits on base not in the branch (how far behind).

If behind, rebase:
```bash
git pull origin <base-branch> --rebase
```

**If conflicts occur:**
1. Read each conflicted file to understand both sides
2. Resolve conflicts, preserving the PR's intent while incorporating base changes
3. `git add <resolved-files>` then `git rebase --continue`

After a rebase you must push with `--force-with-lease` in step 6. If you did NOT rebase, use
a plain push.

### 3. Triage: Reason About Each Comment

This is the critical step. Do NOT blindly apply suggestions. For each comment, read the
referenced code and surrounding context, then classify it:

| Classification | Meaning | Action |
| --- | --- | --- |
| **Real bug** | The issue would cause incorrect behavior, a crash, a security issue, or a test failure. | Fix it. |
| **Valid improvement** | Not a bug but a legitimate quality concern (missing error handling, unclear naming, edge case, race condition). | Fix it. |
| **Style nit / preference** | Formatting, import ordering, subjective taste. | Apply only if it matches repo conventions; otherwise skip with a short reply. |
| **False positive** | The suggestion is wrong, would break behavior, or the comment misreads the code. | Skip the code change. Reply explaining why. |
| **Question / discussion** | Not actionable; the reviewer is asking a question or starting a discussion. | Reply briefly. Do not resolve. |

#### How to reason about a comment

1. Read the file and the specific lines the comment references
2. Read surrounding code (the function, the caller, the test) to understand context
3. If there is a ```suggestion block, evaluate whether the suggested code is correct:
   - Does it compile / type-check?
   - Does it match the existing patterns in the file?
   - Would it introduce a new bug?
   - Is it testing the right thing?
4. If the comment is prose feedback, identify the concrete issue and decide if it is valid
5. Check if the comment has already been addressed by a later commit (diff may have moved on)

Keep a triage list as you go:
```
Comment #1234 (file.ts:42) - REAL BUG - missing null check on user.id
Comment #1235 (file.ts:87) - FALSE POSITIVE - variable is guaranteed non-null by the schema
Comment #1236 (utils.ts:15) - STYLE NIT - prefer const over let (matches repo convention, will fix)
Comment #1237 (api.ts:203) - QUESTION - reviewer asks about rate limiting strategy
```

Address P0/P1 severity tags first if present.

### 4. Fix

For each comment classified as **real bug** or **valid improvement**:

1. Read the file and surrounding code referenced by the comment
2. If the comment includes a ```suggestion block, apply the suggested code (adapting to match
   existing style, formatting, and imports)
3. If the comment is prose feedback, understand the issue and implement the fix
4. Read the file again after editing to confirm the change is correct

**Group related comments that touch the same file.** Apply all changes to a file before
moving to the next. This avoids line-drift issues where an early edit shifts line numbers
for a later comment on the same file.

**Handle line drift:** if a comment references line 42 but you have already edited that
file, re-read the file and locate the correct code by content, not line number.

For each comment classified as **false positive** or **style nit (skipped)**: do not change
the code. Prepare a short reply (see step 6).

For each comment classified as **question / discussion**: prepare a short reply. Do not
resolve the thread.

### 5. Format and Verify

Run the project's format, lint, typecheck, and test commands. Discover them by reading
`package.json`, `Makefile`, `pyproject.toml`, or the CI config (`.github/workflows/`).

Typical commands:
```bash
npm run format        # or: prettier --write .
npm run lint          # or: eslint .
npm run typecheck     # or: tsc --noEmit
npm test              # or: pytest, go test ./..., etc.
```

If formatting changes the applied code (e.g. prettier rewrites), let it. Re-read the
formatted file to confirm the fix is still correct.

If any check fails, fix the failure before proceeding. Do not push broken code.

### 6. Commit and Push

```bash
git add -A
git commit -m "fix: address review comments on PR #<number>

- <one bullet per fix, referencing what was wrong>
- <e.g. Add null check on user.id in auth.ts (comment by @reviewer)>

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>"
```

If the commit message contains special characters (quotes, backticks), use a heredoc:
```bash
git commit -F - <<'EOF'
fix: address review comments on PR #<number>

- <bullets>

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>
EOF
```

Push to the PR branch. If you rebased in step 2, history was rewritten, so use
`--force-with-lease` (safer than `--force`: it refuses to overwrite if the remote moved):
```bash
git push origin <branch-name> --force-with-lease
```

If you did NOT rebase, use a plain push:
```bash
git push origin <branch-name>
```

### 7. Reply to Every Comment and Resolve Threads

For **every** triaged comment, post a short reply on GitHub. Use `gh` to reply to review
threads. The reply should be one sentence, never more than two.

The `/comments/<comment-id>/replies` endpoint posts a threaded reply to the original review
comment. `<comment-id>` is the REST comment ID (`databaseId` in GraphQL).

**For fixed comments:**
```bash
gh api repos/<owner>/<repo>/pulls/<number>/comments/<comment-id>/replies \
  -X POST \
  --field body="Fixed in <short-sha>."
```

**For false positives (skipped):**
```bash
gh api repos/<owner>/<repo>/pulls/<number>/comments/<comment-id>/replies \
  -X POST \
  --field body="Skipping - <one sentence reason, e.g. variable is guaranteed non-null by the schema validation in line 12>."
```

**For style nits (skipped):**
```bash
gh api repos/<owner>/<repo>/pulls/<number>/comments/<comment-id>/replies \
  -X POST \
  --field body="Skipping - <e.g. repo convention uses let in this pattern; see other files in dir/>."
```

**For questions (not resolved):**
```bash
gh api repos/<owner>/<repo>/pulls/<number>/comments/<comment-id>/replies \
  -X POST \
  --field body="<brief answer>."
```

Keep replies short. Examples of good replies:
- "Fixed in a1b2c3d."
- "Skipping - this field is optional and defaults to null per the schema."
- "Good catch, fixed - added the missing error handler."
- "Already handled in the validateInput() call above."

#### Resolve threads

After replying, resolve the threads for comments that were **fixed** or **skipped as false
positive / style nit**. Do NOT resolve question / discussion threads.

Use the GraphQL API to resolve review threads:
```bash
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {threadID: "<thread-id>"}) {
    thread { id isResolved }
  }
}'
```

To find thread IDs, query the PR's review threads:
```bash
gh api graphql -f query='
query {
  repository(owner: "<owner>", name: "<repo>") {
    pullRequest(number: <number>) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          comments(first: 1) { nodes { databaseId body } }
        }
      }
    }
  }
}'
```

Match each thread to its comment by `databaseId` (which equals the comment ID from the
REST API). Resolve only the threads you have replied to and that are not questions.

### 8. Wait for CI

After pushing, watch CI checks:

```bash
gh pr checks <url> --watch --interval 30
```

This blocks until all checks complete. If any check fails:

1. Read the failure logs: `gh pr checks <url> --json name,state,link` then fetch logs
2. Determine whether the failure is caused by your changes or pre-existing:
   - If the failing file/area is **not touched by the PR**, check whether the same check
     fails on the base branch before spending time on it.
   - Do not assume a failure is flaky. Read the log first, and check the check's recent pass
     rate. If it passes consistently elsewhere, treat it as real and investigate.
   - If the branch is behind base, a rebase (step 2) may clear staleness failures.
3. If caused by your changes: fix the issue, commit, push, and re-watch
4. If genuinely pre-existing / flaky: note it and proceed (but do not approve if a required
   check is failing)

**Max retries: 3.** If CI fails 3 times due to your changes, stop, report the failure, and
ask the user for guidance. Do not keep pushing fixes in a loop.

If CI was already green before your push (unlikely but possible), confirm it is still green
after your push.

### 9. Approve or Say Done

The goal of this skill is a **fully fixed, merge-ready PR**. Do not approve (or declare done)
until every one of these is true, verified against the live API:

- [ ] Every actionable comment (real bug / valid improvement) has a corresponding code fix
- [ ] Every triaged comment has a reply (fixed / skipped+reason / answered)
- [ ] Every fixed and false-positive/nit thread is resolved (questions left open)
- [ ] All local checks pass (format, lint, typecheck, tests)
- [ ] Changes are committed and pushed to the PR branch
- [ ] CI is green (all required checks passing)

Only when the PR is fully fixed and CI is green do you finalize:

**If the PR author is NOT `factory-droid[bot]`** (someone else's PR), approve it:
```bash
gh pr review <url> --approve --body "All review comments addressed and resolved, CI is green. PR is merge-ready."
```

**If the PR author IS `factory-droid[bot]`** (your own PR):
Do not approve your own PR (GitHub disallows self-approval and it is not meaningful). The
end state is still a fully fixed, green PR; simply report "Done" to the user.

To determine authorship, check the `author.login` field captured in step 1. The
factory-droid bot author is `factory-droid[bot]`.

If any checklist item cannot be satisfied (e.g. CI stays red after 3 attempts, or a comment
needs the user's decision), do NOT approve. Report the PR as **Blocked** with the specific
reason and what is needed to unblock.

### 10. Report

Verify comment, thread, CI, and approval state from the **live API immediately before
reporting it** (re-run the relevant `gh` / GraphQL queries). Never report from memory of an
earlier fetch: threads get resolved, CI flips, and reviewers act while you work.

Summarize the full workflow result:
- PR number and title
- Comments found: <N> total, <M> actionable, <K> skipped
- Fixed: one line per fix (file + what changed)
- Skipped: one line per skip with reason
- Questions replied to: one line per question
- Threads resolved: <N> of <M>
- CI status: green / failed / flaky
- PR approved: yes / n/a (own PR) / no (CI failing)
- Final state: "Done" or "Approved" or "Blocked - <reason>"

## What Not to Do

- Do not blindly apply suggestions without reasoning about whether they are correct.
- Do not rebase a branch that is already up to date and green. Rebase only when behind base
  or when staleness is causing CI failures.
- Do not restructure the PR beyond the fixes requested by comments (and a conditional rebase).
- Do not use `git push --force`; use `--force-with-lease` after a rebase.
- Do not report comment/thread/CI/approval state from memory; re-verify against the live API.
- Do not add tests unless a comment explicitly asks for them.
- Do not push if any verification check (format, lint, typecheck, test) fails.
- Do not apply suggestions that would introduce bugs or break existing behavior. Skip,
  reply, and resolve instead.
- Do not resolve question / discussion threads.
- Do not approve your own PR.
- Do not retry CI fixes more than 3 times.
- Do not leave any comment without a reply. Every triaged comment gets a response.
