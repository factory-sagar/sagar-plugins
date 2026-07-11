---
name: ship
version: 1.2.0
description: |
  Land finished work. Commits and pushes, writes the repository-template PR body, watches
  current-head CI, closes review threads, and reports merge-ready; merges only when the user
  explicitly requests it and every delivery gate passes.
---

# Ship

Take the current branch from "code done" to "merge-ready". If there is nothing to land
(clean tree, no unpushed commits, no open PR for the branch), say so and stop.

## Workflow

### 1. Preflight

```bash
git status --porcelain && git log origin/$(git rev-parse --abbrev-ref HEAD)..HEAD --oneline 2>/dev/null
gh pr view --json number,url,title,body,baseRefName 2>/dev/null
```

Establish: uncommitted changes? unpushed commits? existing PR? Never ship from the default
branch — create a branch first if needed.

### 2. Commit

If the tree is dirty, review the full diff, then delegate the message to the
`commit-message-writer` droid and commit. Split unrelated changes into separate commits.
Check the staged diff for secrets, credentials, and generated noise.

### 3. Push

```bash
git push -u origin HEAD
```

### 4. PR create or update

- **No PR yet**: create it with a Conventional Commits title and link a ticket when one
  exists. Follow the `create-pr` skill when installed.
- **PR exists**: if this push meaningfully changed scope, regenerate the body.

In both cases the body comes from the `pr-describer` droid and must conform to the repo's
PR template (look in `.github/`, `docs/`, or `PULL_REQUEST_TEMPLATE*`). The body describes
the change itself, never the agent process or tooling that produced it. Include the
Deviations log as reviewer notes when one exists.

End the body with `<!-- pr-body-head=<full-head-sha> -->`. The `guardrails` plugin's stop
hook, when installed, uses this marker to prove that the body describes the current pushed
revision.

### 5. Watch CI until green

Run `gh pr checks --watch`, read failure logs, distinguish change-caused failures from
baseline failures, delegate to `debugger` when the mechanism is unclear, fix and repush.
The review plugin's `review-pr/fix-comments.md` provides the expanded procedure when
installed. Stop after three unsuccessful fix attempts and report the blocker.

### 6. Resolve review threads

If the PR has unresolved review comments, handle them with `review-pr` comments mode
(fix valid ones, reply to every comment, resolve threads). Skip silently if there
are none yet.

### 7. Report merge-ready

End with a short report:

- PR URL, title, and one-line summary
- CI: green (or what is red and why it is pre-existing)
- Threads: resolved / outstanding
- Deviations: from the implementation log, or `none`

Merge only when the current request explicitly authorizes it. When the review plugin is
installed, apply the landing gate from `review-pr` before merging. Otherwise re-fetch
current-head CI, PR-body freshness, and review threads; any unresolved state blocks merge.

## Anti-patterns

- Ending the turn between push and CI result. The watch loop is part of shipping.
- Writing the PR body yourself instead of delegating to `pr-describer`.
- Describing the agent process instead of the change.
- Looping more than 3 fix attempts on red CI without reporting back.
- Merging without explicit instruction in the current request.
