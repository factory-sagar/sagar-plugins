---
name: ship
version: 1.8.0
description: |
  Land finished work. Commits and pushes, writes the repository-template PR body, watches
  current-head CI, closes review threads, and reports merge-ready; merges only when the user
  explicitly requests it and every delivery gate passes.
---

# Ship

Take the current branch from "code done" to a trustworthy merge-ready handoff. Success means
the branch is locally verified, its PR body describes the current change, current-head CI and
review threads are resolved, and merge happens only when the request authorizes it. If there is
nothing to land (clean tree, no unpushed commits, no open PR for the branch), say so and stop.

## Boundaries

- **Branch and local-gate integrity.** Never ship from the default branch — create a branch first
  if needed. Do not push while any locally runnable required check is failing.
- **Push integrity.** Use the plain push command below. Do not pipe push output through `tail`,
  `tee`, `grep`, or another consumer. If a diagnostic pipeline is unavoidable, the same Execute
  command must begin with `set -o pipefail;` so a failed push cannot be hidden by a successful
  downstream command. `--force-with-lease` is allowed only for the initial post-rebase push.
  After any successful push, do not amend the pushed commit: every CI or review correction must
  be a new corrective commit, re-verified locally, and pushed fast-forward.
- **Review continuity.** Preserve `reviewedHeadSha` through this workflow. A head-changing
  correction must rerun synchronization, local verification, commit if needed, and one delta
  verification pass through `review-pr` before it supplies a replacement `reviewedHeadSha`.
  Never exceed review-pr's three-pass delta loop budget in the same user request. If the budget
  is exhausted with findings remaining, stop as blocked and report that a new user instruction
  resets the loop budget.
- **PR-body ownership and freshness.** The body comes from the `pr-describer` droid and must
  conform to the repo's PR template. It describes the change itself, never the agent process or
  tooling that produced it. End it with `<!-- pr-body-head=<full-head-sha> -->`.
- **Foreground CI watch.** Run `gh pr checks --watch --interval 10` in the foreground. Do not background it, poll a
  background log, retry Stop, or emit an interim/final response while it is
  running. After it exits, run one plain `gh pr checks` refresh; if that shows a pending check,
  rerun the foreground watch before continuing.
- **Fix-attempt cap.** Stop after three unsuccessful fix attempts and report the blocker.
- **Merge authority.** Merge only when the current request explicitly authorizes it. When the
  review plugin is installed, apply the landing gate from `review-pr` before merging. In a handoff
  with `reviewedHeadSha`, its final API operation immediately before merge re-fetches live
  `headRefOid` and requires equality with that SHA, with no intervening call. Otherwise re-fetch
  current-head CI, PR-body freshness, and review threads; any unresolved state blocks merge.

## Workflow

### 1. Preflight

```bash
git status --porcelain && git log origin/$(git rev-parse --abbrev-ref HEAD)..HEAD --oneline 2>/dev/null
gh pr view --json number,url,title,body,baseRefName 2>/dev/null
```

Establish: uncommitted changes? unpushed commits? existing PR?

### 1b. Prove CI parity

Read every required workflow under `.github/workflows/` and the repository's master
verification script. Build a matrix:

| Required check | Local command | Result or remote-only reason |
| --- | --- | --- |

Run every safe local equivalent before committing or pushing. A convenience aggregate such
as `verify:quick` is not evidence that standalone metadata, AGENTS, generated-file, lockfile,
formatting, policy, or deployment validators ran. If a required check cannot run locally,
name the exact remote-only dependency and keep it in the CI watch set.

### 2. Commit

If the tree is dirty, review the full diff, then delegate the message to the
`commit-message-writer` droid and commit. Split unrelated changes into separate commits.
Check the staged diff for secrets, credentials, and generated noise.

### 3. Push

```bash
git push -u origin HEAD
```

Use a plain, fast-forward push after local verification and any required broad-review pre-push
verification loop.

### 4. PR create or update

- **No PR yet**: create it with a Conventional Commits title and link a ticket when one
  exists.
- **PR exists**: if this push meaningfully changed scope, regenerate the body.

In both cases, obtain the body from the `pr-describer` droid using the repo's PR template
(look in `.github/`, `docs/`, or `PULL_REQUEST_TEMPLATE*`). Include the Deviations log as
reviewer notes when one exists. The `guardrails` plugin's stop hook, when installed, uses the
head marker to prove that the body describes the current pushed revision.

If the PR is a draft and the requested end state is merge-ready, mark it ready after the
current-head body is stamped and before the final CI watch. Ready-only checks must have a chance
to register before completion is assessed.

### 5. Watch CI until green

Read failure logs, distinguish change-caused failures from baseline failures, delegate to
`debugger` when the mechanism is unclear, fix, create a new corrective commit, and repush. For a
broad or high-consequence review, rerun synchronization, local verification, and one delta
verification pass (subject to review-pr's loop budget) before the plain corrective push. The
review plugin's `review-pr/fix-comments.md` provides the expanded procedure when installed.

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
