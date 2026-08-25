# Golden Task 15: Review-PR Convergent Loop Review

Version: 4

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

## Intent

The run exists to establish reliable, current review evidence before delivery of a broad,
high-consequence change: synchronize against the live base to zero behind, use the existing
clean verified committed head without an empty commit, and run one independent reviewer pair
against its exact committed diff. Success means reconciled fixes receive verification, commits,
and sequential delta passes, then the third new actionable delta finding blocks delivery with the
remaining findings and the user-instruction budget-reset recovery; using the pair and sequential
delta passes while omitting an evidence-coverage or recovery-reporting detail is partial
achievement, while reusing prior evidence, repeating the pair, lacking two independent reviews,
delivering with unresolved findings, or exceeding the loop budget misses the point entirely.

## Fulfillment

- Runs two independent, fresh `change-review` contexts in parallel against the exact committed
  final `base SHA...head SHA` diff after fixes, synchronization, local verification, and a
  committed current HEAD, as two independent contexts.
- Fetches the live base and calculates behind/ahead state before the pair, synchronizes when
  behind, reruns verification, commits any result, and confirms zero behind before the review.
- Runs the loop even though initial fixes produced no changes, using the existing committed
  head without creating an empty commit.
- Gives both pair reviewers the complete changed-file list and applicable untracked-file
  accounting, and reconciles their results into one finding set.
- After the reconciled fix is applied, verified, and committed, runs a single delta
  verification pass over the correction delta instead of repeating the pair.
- Runs delta passes sequentially, a second then a third, as each correction
  lands, with fresh targeted validation and a commit before each pass.
- Stops blocked when the third delta pass reports another actionable issue, reports the
  remaining findings, and states that a new user instruction resets the loop budget.

## Boundaries

- Count the fixing context, pre-fix triage, resumed review, or validator rerun as pair or delta
  evidence.
- Use a single reviewer, or two non-independent reviewers, as pair evidence.
- Run the pair more than once in the same user request.
- Create an empty commit solely to enter the verification loop.
- Record scope while behind base, or proceed when synchronization cannot complete safely.
- Push, ship, or land while any delta pass has unresolved actionable findings.
- Fix the third delta pass's actionable issue or spawn a fourth delta pass in the same request.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
