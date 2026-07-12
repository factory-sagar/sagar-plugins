---
name: ship
version: 1.4.0
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

### 1b. Prove CI parity

Read every required workflow under `.github/workflows/` and the repository's master
verification script. Build a matrix:

| Required check | Local command | Result or remote-only reason |
| --- | --- | --- |

Run every safe local equivalent before committing or pushing. A convenience aggregate such
as `verify:quick` is not evidence that standalone metadata, AGENTS, generated-file, lockfile,
formatting, policy, or deployment validators ran. If a required check cannot run locally,
name the exact remote-only dependency and keep it in the CI watch set.

Do not push while any locally runnable required check is failing.

### 2. Commit

If the tree is dirty, review the full diff, then delegate the message to the
`commit-message-writer` droid and commit. Split unrelated changes into separate commits.
Check the staged diff for secrets, credentials, and generated noise.

### 3. Push

```bash
git push -u origin HEAD
```

Use a plain, fast-forward push after local verification and any required broad-review final-head
gate. `--force-with-lease` is allowed only for the initial post-rebase push. After any successful
push, do not amend the pushed commit: every CI or review correction must be a new corrective
commit, re-verified locally, and pushed fast-forward.

When `review-pr` hands off `finalReviewedHeadSha`, preserve it through this workflow. A
head-changing correction must rerun synchronization, local verification, commit if needed, and
the full two-review final-head gate before it supplies a replacement `finalReviewedHeadSha`.

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
baseline failures, delegate to `debugger` when the mechanism is unclear, fix, create a new
corrective commit, and repush. For a broad or high-consequence review, rerun synchronization,
local verification, and the full two-review final-head gate before the plain corrective push.
The review plugin's `review-pr/fix-comments.md` provides the expanded procedure when installed.
Stop after three unsuccessful fix attempts and report the blocker.

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
installed, apply the landing gate from `review-pr` before merging. In a handoff with
`finalReviewedHeadSha`, its final API operation immediately before merge re-fetches live
`headRefOid` and requires equality with that SHA, with no intervening call. Otherwise re-fetch
current-head CI, PR-body freshness, and review threads; any unresolved state blocks merge.

## Anti-patterns

- Ending the turn between push and CI result. The watch loop is part of shipping.
- Writing the PR body yourself instead of delegating to `pr-describer`.
- Describing the agent process instead of the change.
- Looping more than 3 fix attempts on red CI without reporting back.
- Merging without explicit instruction in the current request.
