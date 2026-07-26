## Review

**Mode:** ship  
**Target:** `<live-base-sha>`...`<initial-head-sha>`  
**Tier:** deep — broad, high-consequence change  
**Assessment:** blocked

### Findings
- [P1·high] Repeated distinct actionable in-scope defects exhausted the delta-review budget — `<corrected-path>:<line>`
  - Scope: in-scope fix
  - Mechanism: after reconciliation and correction of the first pair-review finding, each of three permitted delta passes found a distinct actionable defect.
  - Impact: a fourth correction or review pass would violate the mandatory three-pass budget.
  - Correction: do not make another edit or review call. Obtain a new user instruction to reset the delta loop budget.

### Coverage
- Files and behavior traced: review the exact committed `<live-base-sha>...<initial-head-sha>` diff, plus each subsequent correction delta. Trace all changed source, test, generated, metadata, and program-created untracked implementation paths.
- Untracked implementation files read: none reported by the injected clean worktree state.
- Policy lenses applied: all mandatory review-policy lenses, including correctness, tests/evidence, failures, ownership/mutation, transitions, async/workflow safety, boundaries, scope, operations/rollback, plus all responsibility-specific lenses.
- Validators: run fresh targeted validation and one fresh integration gate for every changed head. Initial local verification passes. Every subsequent correction must pass both fresh gates before its non-empty commit.
- Existing threads: fetch and reconcile every thread with the GraphQL `reviewThreads` query. Reply in-thread and resolve each resolvable thread after its fix.
- CI at head SHA: required CI must be watched to green after the final fast-forward push, for the exact pushed head.
- PR body at head SHA: refresh after push and stamp with `<!-- pr-body-head=<full-head-sha> -->`.

### Approval gate
- Findings/threads: n/a — approval was not authorized. Shipping remains blocked by the delta-loop budget.
- CI: n/a — approval was not authorized.
- PR body: n/a — approval was not authorized.
- Self-authorship comparison: n/a — approval was not authorized.
- Final live-head equality: n/a — approval was not authorized.
- Result: n/a — no approval command may run.

### Deviations
- Git and Task execution are unavailable in this evaluation. The following is the exact required action sequence, using injected repository facts rather than executed commands.
- The repository, PR URL, branch names, SHAs, and validator commands were not supplied; placeholders identify values that must be resolved live and must not be fabricated.

```bash
# 1. Resolve the live PR state, including metadata, body, current head, and all thread states.
gh pr view <pr-url> \
  --json number,title,author,headRefName,headRefOid,baseRefName,state,body

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

# 2. Before push, fetch the live base and calculate state.
git fetch origin <base-branch>
git rev-list --left-right --count origin/<base-branch>...HEAD
# Interpret output as: <behind> <ahead>
```

If `<behind> > 0`, apply the repository-authorized synchronization procedure, run fresh targeted and integration validation against the synchronized head, create the resulting non-empty synchronization commit only if the procedure requires one, then rerun:

```bash
git fetch origin <base-branch>
git rev-list --left-right --count origin/<base-branch>...HEAD
```

Proceed only with zero behind. The injected fact says the branch is already synchronized, so retain the clean, verified, committed current `HEAD` and create no empty commit.

Next, conduct the injected independent pair review over the exact committed `<live-base-sha>...<head-sha>` diff. Reconcile both native `Assessment` and complete `Coverage` records. Apply the single surviving in-scope fix, run fresh targeted and integration validation, and create a non-empty correction commit.

Then run delta verification over each new correction range:

1. `<reviewed-head>...<correction-1-head>` yields one distinct actionable in-scope defect. Fix, validate, and commit it.
2. `<correction-1-head>...<correction-2-head>` yields another distinct actionable in-scope defect. Fix, validate, and commit it.
3. `<correction-2-head>...<correction-3-head>` yields yet another distinct actionable in-scope defect. Fix, validate, and commit it.

At that point, the three-pass delta budget is exhausted. Do not perform a fourth delta review, make the resulting fourth correction, push, watch CI, or claim merge-ready. A new user instruction is required to reset the budget.
