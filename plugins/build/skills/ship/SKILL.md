---
name: ship
version: 1.0.0
description: |
  Land finished work end-to-end: commit, push, create or update the PR with a
  template-conformant body, watch CI until green (fixing failures), resolve review threads,
  and report merge-ready. Owns everything after "the code is done".
  Use when:
  - The user says "ship it", "push", "push everything", "push and update PR", "push and make a PR"
  - The user says "monitor ci", "verify ci is green", "merge it if CI passes"
  - The user says "clean up the PR", "fix the PR body", "package this up well"
  - Implementation or review-fix is complete and the change needs to land
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
Run Droid Shield-sensitive checks yourself: no secrets, credentials, or generated noise in
the staged diff.

### 3. Push

```bash
git push -u origin HEAD
```

### 4. PR create or update

- **No PR yet**: follow the `create-pr` skill's conventions (Conventional Commits title,
  linked ticket when one exists).
- **PR exists**: if this push meaningfully changed scope, regenerate the body.

In both cases the body comes from the `pr-describer` droid and must conform to the repo's
PR template (look in `.github/`, `docs/`, or `PULL_REQUEST_TEMPLATE*`). The body describes
the change itself — never the session, process, or tooling that produced it. Include the
Deviations log as reviewer notes when one exists.

### 5. Watch CI until green

Run the CI watch loop exactly as defined in the `fix-pr` skill (step "Wait for CI"):
`gh pr checks --watch`, read failure logs, distinguish own-change failures from
pre-existing ones, delegate to the `debugger` droid when the cause is not obvious, fix and
repush. Max 3 fix attempts, then stop and report.

### 6. Resolve review threads

If the PR has unresolved review comments, handle them with the `fix-pr` skill's triage
rules (fix valid ones, reply to every comment, resolve threads). Skip silently if there
are none yet.

### 7. Report merge-ready

End with a short report:

- PR URL, title, and one-line summary
- CI: green (or what is red and why it is pre-existing)
- Threads: resolved / outstanding
- Deviations: from the implementation log, or `none`

Do not merge. Merging stays a human action unless the user explicitly asked for
merge-on-green in this session.

## Anti-patterns

- Ending the turn between push and CI result. The watch loop is part of shipping.
- Writing the PR body yourself instead of delegating to `pr-describer`.
- Describing the process ("this session refactored...") instead of the change.
- Looping more than 3 fix attempts on red CI without reporting back.
- Merging without an explicit instruction from this session.
