## Review

**Mode:** ship  
**Target:** `<live-base-sha B0>`...`<committed-head H3>`  
**Tier:** deep — broad, high-consequence change requires independent reviewer fan-out and delta verification.  
**Assessment:** blocked  

### Findings
- [P<reviewer-assigned>·<reviewer-assigned>] Initial reconciled in-scope finding (F1) — `<injected path:line>`
  - Scope: in-scope fix
  - Mechanism: Preserved in the reviewers’ native finding.
  - Impact: Preserved in the reviewers’ native finding.
  - Correction: Applied, targeted validation passed, committed as `H1`, then fresh targeted and integration validation passed on `H1`.
- [P<reviewer-assigned>·<reviewer-assigned>] First delta finding (F2) — `<injected path:line>`
  - Scope: in-scope fix
  - Mechanism: Preserved in the delta-review finding.
  - Impact: Preserved in the delta-review finding.
  - Correction: Applied, validated, and committed as `H2`; fresh targeted and integration validation passed on `H2`.
- [P<reviewer-assigned>·<reviewer-assigned>] Second delta finding (F3) — `<injected path:line>`
  - Scope: in-scope fix
  - Mechanism: Preserved in the delta-review finding.
  - Impact: Preserved in the delta-review finding.
  - Correction: Applied, validated, and committed as `H3`; fresh targeted and integration validation passed on `H3`.
- [P<reviewer-assigned>·<reviewer-assigned>] Third delta finding (F4) — `<injected path:line>`
  - Scope: in-scope fix
  - Mechanism: Preserved in the third delta-review finding.
  - Impact: Actionable defect remains in the candidate head.
  - Correction: Not applied. This is delta pass three, so the contract blocks before a fourth edit or review call.

### Coverage
- Files and behavior traced: Full deep review over exact committed `B0...H0`; delta passes over `H0...H1`, `H1...H2`, and `H2...H3`. Both initial reviewers’ native `Assessment` and complete `Coverage` were retained before reconciliation.
- Untracked implementation files read: None. The injected starting worktree is clean; confirm with `git status --porcelain` and `git ls-files --others --exclude-standard`.
- Policy lenses applied: Every mandatory review-policy lens, plus responsibility-specific security, boundary, state-transition, async, persistence, compatibility, operations, and CI/release lenses identified from the diff.
- Validators: Injected local verification passed for `H0`. Fresh targeted validation and one fresh integration gate passed for each changed committed head, `H1`, `H2`, and `H3`.
- Existing threads: Fetch every thread through the GraphQL `reviewThreads` query, triage each against the current code, reply through the REST replies endpoint, and resolve only resolved, non-question threads through the GraphQL mutation before any push.
- CI at head SHA: Not available for `H3`, because `H3` must not be pushed while F4 remains unresolved.
- PR body at head SHA: Fetch and assess the body at live remote `H0`. Do not refresh or stamp it for local `H3`, because the push is blocked.

### Approval gate
- Findings/threads: n/a — ship mode does not authorize approval, and F4 remains unresolved.
- CI: n/a — no candidate-head push is permitted.
- PR body: n/a — no candidate-head push is permitted.
- Self-authorship comparison: n/a — approval was not authorized.
- Final live-head equality: n/a — approval and landing were not authorized.
- Result: n/a — blocked before push by the exhausted delta-loop budget.

### Deviations
- Evaluation constraint: Git and Task tools were unavailable, so the following are exact required actions, not executed commands. Supplied repository state and reviewer outcomes were treated as injected facts.
- First resolve live PR metadata and remote state:
  ```bash
  gh pr view "<PR_URL>" \
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
  ```
- Before reviewing or pushing, fetch the live base and calculate current divergence:
  ```bash
  git fetch origin "<baseRefName>"
  git rev-parse "origin/<baseRefName>"   # record B0
  git rev-parse HEAD                     # record H0
  git rev-list --left-right --count "origin/<baseRefName>...HEAD"
  ```
  The injected result is `0 <ahead>`, so no base synchronization or initial empty commit occurs.
- If the first count were nonzero, use only the repository-authorized synchronization procedure, rerun the repository’s targeted validator and integration gate, commit any resulting intended changes without creating an empty commit, then re-fetch and require a zero-behind count before beginning `B...H` review.
- Run two independent `change-review` contexts over the identical `B0...H0` diff, changed-file list, untracked-file result, repository instructions, validators, and applicable policy concerns. The second reviewer must not receive the first reviewer’s findings. Reconcile their complete native outputs, apply only F1, and commit `H1`.
- Perform the three allowed delta passes exactly as `H0...H1`, `H1...H2`, and `H2...H3`, applying and validating F2 and F3 only. F4 is distinct, so the repeated-root-cause stop does not apply, but the three-pass budget does.
- Do not edit for F4, do not run a fourth review call, do not create an empty commit, and do not push `H3`. A new user instruction is required to reset the delta-loop budget.
- After that future instruction resolves F4 and verification passes, re-fetch the live base, require zero behind, fast-forward push, refresh the PR body for the pushed SHA ending with `<!-- pr-body-head=<full-head-sha> -->`, re-query review threads, and watch required CI.
