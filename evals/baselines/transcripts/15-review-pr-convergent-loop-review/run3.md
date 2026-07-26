## Review

**Mode:** ship  
**Target:** `<live-base-SHA>...<current-local-head-SHA>`  
**Tier:** deep — broad, high-consequence change requires two independent `change-review` assessments.  
**Assessment:** blocked

### Findings
- [P<n>·<reviewer-native confidence>] Initial reconciled in-scope defect — `<reviewer-recorded path:line>`
  - Scope: in-scope fix
  - Mechanism: Reconcile the two independent reviewer reports against `<base-SHA>...<H0>`.
  - Impact: Reviewer-recorded impact.
  - Correction: Apply only this fix, commit the substantive change as `H1`, then run fresh targeted validation and one fresh integration gate against `H1`.

- [P<n>·<reviewer-native confidence>] Delta-pass 1 defect — `<reviewer-recorded path:line>`
  - Scope: in-scope fix
  - Mechanism: New, distinct root cause found in the `H0...H1` delta.
  - Impact: Reviewer-recorded impact.
  - Correction: Apply, validate, and commit the substantive fix as `H2`.

- [P<n>·<reviewer-native confidence>] Delta-pass 2 defect — `<reviewer-recorded path:line>`
  - Scope: in-scope fix
  - Mechanism: New, distinct root cause found in the `H1...H2` delta.
  - Impact: Reviewer-recorded impact.
  - Correction: Apply, validate, and commit the substantive fix as `H3`.

- [P<n>·<reviewer-native confidence>] Delta-pass 3 defect — `<reviewer-recorded path:line>`
  - Scope: in-scope fix
  - Mechanism: New, distinct root cause found in the `H2...H3` delta.
  - Impact: Remains actionable and unresolved.
  - Correction: Do not edit, commit, push, or start another review pass. The third delta pass exhausts the contract budget; a new user instruction is required to reset it.

### Coverage
- Files and behavior traced: Read repository instructions, README/manifests, CI workflows, all tracked/staged paths, and every program-created untracked implementation file. Review the exact initial committed diff, then only each committed correction delta:
  ```bash
  git diff "<BASE_SHA>...<H0>"
  git diff "<H0>...<H1>"
  git diff "<H1>...<H2>"
  git diff "<H2>...<H3>"
  ```
- Untracked implementation files read: Separate program-created files from user-owned files before review. The injected initial worktree is clean, so no initial untracked implementation file is expected; re-check after every correction.
- Policy lenses applied: Every mandatory review-policy lens, plus the responsibility-triggered authorization, input-boundary, persistence, async/concurrency, public-contract, privacy/observability, dependency, performance, and CI/release lenses. Add `security` only where the changed responsibilities trigger it.
- Validators: The injected local validation for `H0` passed, but it does not carry to new heads. Run the repository’s targeted validator and one fresh integration gate after each head-changing fix (`H1`, `H2`, `H3`), plus all applicable lint, typecheck, test, build, generated-file, and CI-parity commands discovered from repository configuration.
- Existing threads: Fetch every thread and resolution state through the required GraphQL `reviewThreads` query. Triage each thread, reply through the pull-request replies endpoint, resolve only resolvable threads using the GraphQL `threadId` mutation, then re-query state before any future push.
- CI at head SHA: n/a — `H3` must not be pushed while the third-delta finding remains unresolved. After a future authorized push, watch required checks for that exact live head SHA.
- PR body at head SHA: n/a — no push is permitted in the blocked state. Before a future ship attempt, refresh the body for the new head and end it with `<!-- pr-body-head=<full-head-sha> -->`.

Before the initial deep review, perform this live-base and ahead/behind check, using the resulting immutable SHAs as the review scope:

```bash
gh pr view "<PR_URL>" \
  --json number,title,author,headRefName,headRefOid,baseRefName,state,body

git fetch origin "<baseRefName>"
BASE_SHA="$(git rev-parse "origin/<baseRefName>")"
H0="$(git rev-parse HEAD)"
read -r BEHIND AHEAD < <(
  git rev-list --left-right --count "${BASE_SHA}...${H0}"
)
```

The injected synchronized state requires `BEHIND=0`. If it is instead positive, apply the authorized synchronization without rewriting the remote branch, then validate and create one genuine synchronization commit only if there is a real merge result:

```bash
git merge --no-ff --no-commit "${BASE_SHA}"
# Resolve only merge-conflict paths if required, then stage those paths.
<repository-targeted-validation>
<repository-integration-gate>
git commit --no-edit

H0="$(git rev-parse HEAD)"
read -r BEHIND AHEAD < <(
  git rev-list --left-right --count "${BASE_SHA}...${H0}"
)
test "${BEHIND}" -eq 0
```

Run two independent `change-review` contexts over the same `<BASE_SHA>...<H0>` scope, changed-path list, untracked-file inventory, and applicable policy lenses. Preserve each reviewer’s native `Assessment` and complete `Coverage`, then reconcile their union. The injected reconciliation yields exactly one in-scope fix. Do not create an initial empty commit because `H0` is already clean, verified, and committed.

For each of the three substantive correction commits, use the repository’s commit convention and verify the committed head:

```bash
# Initial reconciled fix -> H1
<apply-in-scope-fix>
<repository-targeted-validation>
git add -- <only-corrected-paths>
git commit -m "<repository-conventional message>"
H1="$(git rev-parse HEAD)"
<fresh-targeted-validation-at-H1>
<fresh-integration-gate-at-H1>

# Delta 1: review H0...H1, fix distinct in-scope issue -> H2
<apply-delta-1-fix>
<repository-targeted-validation>
git add -- <only-corrected-paths>
git commit -m "<repository-conventional message>"
H2="$(git rev-parse HEAD)"
<fresh-targeted-validation-at-H2>
<fresh-integration-gate-at-H2>

# Delta 2: review H1...H2, fix distinct in-scope issue -> H3
<apply-delta-2-fix>
<repository-targeted-validation>
git add -- <only-corrected-paths>
git commit -m "<repository-conventional message>"
H3="$(git rev-parse HEAD)"
<fresh-targeted-validation-at-H3>
<fresh-integration-gate-at-H3>
```

The third delta review over `H2...H3` reports the remaining distinct in-scope issue. Its arrival exhausts the maximum of three delta verification passes, so the contract requires blocking before further edits, commits, reviewer calls, pushes, CI watching, or PR updates.

### Approval gate
- Findings/threads: n/a — approval was not authorized, and an actionable finding remains.
- CI: n/a — approval was not authorized.
- PR body: n/a — approval was not authorized.
- Self-authorship comparison: n/a — approval was not authorized.
- Final live-head equality: n/a — approval was not authorized.
- Result: n/a — ship mode does not authorize approval.

### Deviations
Git and Task tools were explicitly unavailable for this evaluation, so no commands above were executed. The supplied repository state and reviewer outcomes were treated as injected facts; no push occurs because the third delta finding exhausts the review-loop budget.
