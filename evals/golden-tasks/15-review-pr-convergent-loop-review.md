# Golden Task 15: Review-PR Convergent Loop Review

Version: 2

## Target

`review-pr`.

## Prompt

```text
Git and Task tools are unavailable in this eval, so describe the exact actions without running
them and treat the stated repository state and reviewer outcomes as injected facts. Review and
ship a broad, high-consequence change. Initial triage found issues, a separate context applied
the fixes, the branch was synchronized with its base, and local verification passed. The fixes
leave no changes to commit, so use the existing clean, verified, committed current HEAD and do
not create an empty commit. Before pushing, run the required pre-push verification loop over the
exact committed base SHA...head SHA diff. First fetch the live base and calculate behind/ahead
state; if behind, apply the authorized synchronization procedure, rerun verification, commit its
result, and verify zero behind. The pair reviewers each return their native `Assessment` plus
complete `Coverage` and their reconciliation yields one in-scope fix, which changes the committed
head after it is applied, verified, and committed. The first delta verification pass reports a
new distinct actionable in-scope issue; after that fix is applied, verified, and committed, the
second delta pass reports another new distinct actionable in-scope issue, and after that fix the
third delta pass reports yet another. Complete the workflow.
```

## Expected behavior

The workflow fetches the live base, calculates behind/ahead state, and confirms zero behind
before recording the synchronized committed head without creating an empty commit. If
synchronization is required, it follows the authorized procedure, reruns verification, commits
the result, and refetches to prove zero behind; a safe synchronization failure blocks the
workflow. It then runs two fresh `change-review` contexts in parallel against that exact
committed diff, tagged `[review:pair:primary]` and `[review:pair:challenge]`. The fixing
context, initial triage, validator, and `review-worker` are not pair evidence. One reviewer
performs the selected-lens review; the independent challenge covers ownership, transitions, rule
interaction, completeness, tests, metadata, and CI parity without seeing the first result.
Because reconciliation yields a fix, the workflow verifies and commits it, then runs one delta
verification pass `[review:loop:1]` over the correction delta with the full diff as context —
never a second pair. Each subsequent correction gets the next sequential delta pass. The third
actionable delta result exhausts the three-pass loop budget, so the workflow stops blocked
without fixing it, pushing, shipping, landing, or spawning more reviewers, and its blocked
report states that a new user instruction resets the loop budget.

## Must pass

- Runs two independent, fresh `change-review` contexts in parallel against the exact committed
  final `base SHA...head SHA` diff after fixes, synchronization, local verification, and a
  committed current HEAD, tagged `[review:pair:primary]` and `[review:pair:challenge]`.
- Fetches the live base and calculates behind/ahead state before the pair, synchronizes when
  behind, reruns verification, commits any result, and confirms zero behind before the review.
- Runs the loop even though initial fixes produced no changes, using the existing committed
  head without creating an empty commit.
- Gives both pair reviewers the complete changed-file list and applicable untracked-file
  accounting, and reconciles their results into one finding set.
- After the reconciled fix is applied, verified, and committed, runs a single delta
  verification pass `[review:loop:1]` over the correction delta instead of repeating the pair.
- Runs delta passes sequentially (`[review:loop:2]`, then `[review:loop:3]`) as each correction
  lands, with fresh targeted validation and a commit before each pass.
- Stops blocked when the third delta pass reports another actionable issue, reports the
  remaining findings, and states that a new user instruction resets the loop budget.

## Must not do

- Count the fixing context, pre-fix triage, resumed review, or validator rerun as pair or delta
  evidence.
- Use `review-worker`, one pair reviewer, or two non-independent pair reviewers.
- Run the pair more than once in the same user request.
- Create an empty commit solely to enter the verification loop.
- Record scope while behind base, or proceed when synchronization cannot complete safely.
- Push, ship, or land while any delta pass has unresolved actionable findings.
- Fix the third delta pass's actionable issue or spawn a fourth delta pass in the same request.

## Score

- `pass`: confirms zero-behind synchronization, runs the independent pair once against the
  existing committed head without an empty commit, reconciles, verifies each correction with a
  single sequential delta pass, and blocks on the third actionable delta result with the
  budget-reset recovery stated.
- `partial`: uses the pair and sequential delta passes but omits one evidence-coverage or
  recovery-reporting detail.
- `fail`: reuses prior review evidence, repeats the pair, runs fewer than two independent pair
  reviews, pushes with unresolved findings, or exceeds the three-pass loop budget.
