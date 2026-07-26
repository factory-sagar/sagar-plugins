---
name: review-pr
version: 3.2.0
description: |
  Review a PR, branch, commit, or staged change through the mandatory review policy. Plain
  "review" is read-only; explicit approve, fix, comment, ship, and merge wording grants only
  the corresponding stronger authority.
---

# Review PR

Review the requested scope against [`review-policy.md`](./review-policy.md). Choose relevant
lenses from changed responsibilities, not file type alone. Trace changed behavior, read
program-created untracked files, and run the repository's applicable validation commands.

## Authority modes

Choose the narrowest mode authorized by the user's words:

| User intent | Mode | Allowed end state |
| --- | --- | --- |
| `review PR <n>` | `report` | Findings only. No edits, comments, pushes, approvals, or merges. |
| `approve PR <n>` / `approve this PR` / `approve this pull request` | `approve` | Complete the read-only review, then approve only if every approval gate passes. No edits, pushes, or merges. |
| `review and fix PR <n>` | `fix` | Fix valid findings, verify, commit locally, stop before push. |
| `address PR <n>` / `fix review comments` / `fix every review comment on PR <n>` | `comments` | Triage every existing comment, fix, reply, resolve, push, and watch CI. |
| `ship` / `push and make merge-ready` | `ship` | Push, refresh the PR, watch CI, resolve threads, report merge-ready. |
| `merge PR <n>` / `approve and merge PR <n>` / `approve and land this PR` | `land` | `ship`, then merge only after every hard gate passes. Combined approval wording also runs the approval gate. |

Words describing quality (`thorough`, `deep`, `security`) change depth, never authority. A
plain review stays read-only however serious the diff. `merge`, `land`, `ship`, and "make
merge-ready" wording never grants approval authority. Advice questions such as `Should I approve
PR 42?` authorize nothing. If branch protection requires approval and approval was not
explicitly authorized, report blocked rather than self-approving.

Explicit approval targets a `PR` or `pull request` in the same clause. Approval alone is
read-only. When approval accompanies `comments`, `ship`, or `land`, run the approval gate after
that mode reaches merge-ready.

## Review workflow

1. Resolve the target and, for a PR, fetch its metadata, live head SHA, body, changed files, and
   every review thread with its resolution state, using the API calls in
   [`pr-mechanics.md`](./pr-mechanics.md). Read relevant repository instructions and validation
   commands.
2. Before checking out a PR branch, read `git config --bool --get workflow.disposableCheckout`.
   When it is not `true`, require `git status --porcelain` to be clean and stop if it is not;
   never stash, discard, or overwrite existing work. A disposable checkout may use its authorized
   cleanup procedure.
3. Review tracked, staged, and untracked implementation paths. Program-created untracked files
   are in scope and must be read because a plain `git diff` does not show them. Distinguish them
   from pre-existing user-owned files before deciding scope.
4. Run `change-review` for the requested scope and add `security` when the changed
   responsibilities warrant security review. Reviewer fan-out is bounded per user request. The
   delta verification loop still runs at most three delta verification passes.
5. Reconcile findings against the diff, surrounding code, intent, and validation evidence.
   Each candidate is an **in-scope fix**, **scope-expanding proposal**, or
   **invalid/pre-existing**. Apply only in-scope fixes. A valid defect with only
   scope-expanding remedies stops for a new user decision; the finding does not authorize the
   remedy.
6. In a mutating mode, validate fixes, commit them when needed, and stop or continue only to the
   authorized mode. Do not create an empty commit. For each head-changing correction, run
   fresh targeted validation plus one fresh integration gate for the new head; validation
   evidence from an earlier head does not carry over to changed paths. When the loop budget is exhausted, or
   the same root-cause finding survives two consecutive delta passes, block before any further
   edit or review call, report the remaining findings, and state that a new user instruction
   resets the loop budget. Use [`fix-comments.md`](./fix-comments.md) for comments mode and
   [`deep-review.md`](./deep-review.md) for broad or high-consequence reviews.

A change is broad or high-consequence when it changes more than 10 files, more than 3 approved
units, externally controlled state, multi-phase transitions, migrations, new or materially
rewritten authorization decisions, concurrency, or 3 or more materially distinct risk
responsibilities. A small, well-tested edit to existing risk-sensitive logic remains light only
when none applies.

## Approval gate

Run this gate only when explicit approval was authorized, and only after the
completed normal review. Approval requires a reviewed current head. Before final approval,
verify against the live PR that:

1. There are zero unresolved findings and zero unresolved review threads, confirmed by the
   GraphQL thread query in [`pr-mechanics.md`](./pr-mechanics.md) rather than by REST comments.
2. Required CI is green for the current head SHA.
3. The PR body is current for that head and still describes the PR.
4. The PR author's `author.login` differs from the authenticated user from `gh api user --jq .login`.

If any gate fails, report approval blocked. As the final API operation immediately before
approval, re-fetch the live `headRefOid` and require equality with the reviewed head, with no
intervening call. If the live head differs, stop and require a fresh user review request.
Otherwise execute:

```bash
gh pr review <url> --approve --body "Review complete, required checks are green, and the PR is merge-ready."
```

Reserve `approved` for a successfully executed command. When the command was not executed,
report `would be submitted via gh pr review --approve, but was not executed — <reason>`.
Approval never implies push or merge authority.

## Landing gate

Merge only with explicit instruction. Before merging, verify against the live API that required
CI is green for the current head SHA and zero unresolved review threads remain. Re-fetch the
live head immediately before merging and require it to equal the reviewed head, with no
intervening call. If any gate fails or the head changed, report blocked rather than merging.

## Output

```markdown
## Review

**Mode:** <report | approve | fix | comments | ship | land>
**Target:** <base SHA>...<head SHA>
**Tier:** <light | deep> — <reason>
**Assessment:** <correct | needs changes | blocked | merge-ready | merged>

### Findings
- [P<n>·<confidence>] <title> — `path:line`
  - Scope: <in-scope fix | scope-expanding proposal | invalid/pre-existing>
  - Mechanism:
  - Impact:
  - Correction:

### Coverage
- Files and behavior traced:
- Untracked implementation files read:
- Policy lenses applied:
- Validators:
- Existing threads:
- CI at head SHA:
- PR body at head SHA:

### Approval gate
- Findings/threads:
- CI:
- PR body:
- Self-authorship comparison:
- Final live-head equality:
- Result:

### Deviations
<entries or `none`>
```
