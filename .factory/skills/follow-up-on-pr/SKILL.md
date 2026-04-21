---
name: follow-up-on-pr
description: Follow up on an existing PR by rebasing on the default branch, addressing reviewer comments, fixing CI issues, and pushing updates. Use when the user provides a PR URL or number and wants to get it ready for merge.
---

# Follow Up on PR

Take over an existing PR, bring it up to date, address all feedback, and push it to a merge-ready state.

## Inputs

- **PR URL or number** (required): e.g. `https://github.com/<owner>/<repo>/pull/123` or `#123`
- **Branch name** (optional): If not provided, extract from PR metadata
- **Default branch** (optional): If not provided, infer from repo settings (commonly `main`, `master`, or `dev`)

## Workflow

### 1. Study the PR

Fetch the PR via `FetchUrl` (or `gh pr view <N> --json`) to get:
- File changes (diffs)
- Reviewer comments (inline and general)
- CI workflow status and logs
- PR description and any linked ticket (GitHub issue, Linear, Jira, etc.)

Read all changed files in depth. Understand the intent and scope of the change.

**If the PR fixes a specific issue** (e.g. production error, user-reported bug): investigate the root cause before reviewing the code. Use the project's error tracker (Sentry, Datadog, etc.) or linked ticket to confirm the fix addresses the actual problem. PRs are sometimes superseded by other fixes already merged — check the default branch history before putting more work in.

### 2. Fetch and Check Out the Branch

```bash
git fetch origin <branch-name> <default-branch>
git checkout <branch-name>
```

If the branch doesn't exist locally, `git checkout` will create a tracking branch from `origin/<branch-name>`.

### 3. Rebase on the Latest Default Branch

```bash
git pull origin <default-branch> --rebase
```

**If conflicts occur:**
1. Read each conflicted file to understand both sides
2. Resolve conflicts, preserving the PR's intent while incorporating changes from the default branch
3. `git add <resolved-files>`
4. `git rebase --continue`

**If rebase is clean:** Verify the state with `git log --oneline -5` and `git diff --stat origin/<default-branch>..HEAD`.

### 4. Address Reviewer Comments

Review comments were already fetched in step 1. For each unresolved comment:
1. Read the comment and understand what's being asked
2. Make the code change (or explain why it's not needed)
3. Add tests if requested
4. Commit the fix with a descriptive message

**Already-addressed comments:** Check if a reply already exists (`in_reply_to_id` field on inline comments). Skip comments that have been resolved.

### 5. Run Local CI Checks

Discover the project's check commands from `package.json` scripts, `Makefile`, `justfile`, `pyproject.toml`, `Cargo.toml`, or the CI workflow definitions under `.github/workflows/`. Run them locally, scoped to the files or packages touched by the PR when possible.

Typical commands to look for:

```bash
# Lint + format (autofix)
<lint-fix command>            # e.g. npm run lint -- --fix, ruff check --fix, cargo fmt

# Typecheck
<typecheck command>           # e.g. npm run typecheck, mypy, tsc --noEmit

# Tests
<test command>                # e.g. npm test, pytest, cargo test, go test ./...
```

For monorepos, use the workspace's filter/scope flag so only affected packages run (e.g. `--filter=<workspace>`, `-w <workspace>`, `nx affected`, `bazel test //path/...`).

**Distinguishing pre-existing failures from PR issues:**
Some CI failures exist on the default branch and are unrelated to the PR. If a failure occurs in a file the PR didn't touch, verify it exists on the default branch too before spending time on it. Common pre-existing issues include module resolution errors for recently-added dependencies.

**E2E / integration tests:** If the PR changes user-facing behavior (UI flow, CLI output, API response shape), E2E tests may break even when the code is correct. Read the failing test to understand what it expects, then update it to match the new behavior. Don't assume E2E failures are flaky — read them first.

### 6. Commit and Push

```bash
git add -A
git commit -m "<type>(<scope>): <description>

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>"

git push origin <branch-name> --force-with-lease
```

**If Droid-Shield blocks the push:** This happens when unrelated test fixtures or docs contain strings that look like secrets. The agent cannot override Droid-Shield. Ask the user to push manually or disable Droid-Shield via `/settings`.

### 7. Reply to Reviewer Comments

Reply to each addressed comment so reviewers know their feedback was handled.

**For inline review comments** (the most common type):
```bash
gh api repos/<owner>/<repo>/pulls/<N>/comments/<COMMENT_ID>/replies \
  -X POST \
  -f body="<explanation of what was done>"
```

**For a general PR-level summary:**
```bash
gh pr comment <N> --body "<summary of all changes made>"
```

**To check thread resolution status** (optional):
```bash
gh api graphql -f query='{
  repository(owner: "<owner>", name: "<repo>") {
    pullRequest(number: <N>) {
      reviewThreads(first: 20) {
        nodes {
          isResolved
          comments(first: 3) { nodes { body author { login } } }
        }
      }
    }
  }
}'
```

### 8. Update PR Description

If follow-up changes are significant (new tests, architectural shifts, additional scope), update the PR description:

```bash
gh pr edit <N> --body "<updated description>"
```

Follow the repo's PR template if one exists (check `.github/pull_request_template.md`). At minimum, refresh the "How it was tested" / "Testing" section to reflect any tests added or updated.

## Verification

Before considering the task complete, confirm:
- [ ] Branch is rebased on the latest default branch
- [ ] All reviewer comments are addressed with code changes (or have an explicit reply explaining why not)
- [ ] Local lint, typecheck, and tests pass for affected files/packages
- [ ] Changes are pushed to remote
- [ ] Replies posted to every reviewer comment that triggered a change
- [ ] PR description is up to date
