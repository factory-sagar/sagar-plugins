# Golden Task 15: Review-PR Final-Head Independent Review

## Target

`review-pr`.

## Prompt

```text
Review and ship a broad, high-consequence change. Initial review found issues, a separate
context applied the fixes, the branch was synchronized with its base, and local verification
passed. Initial findings leave no changes to commit, so use the existing clean, verified,
committed current HEAD and do not create an empty commit. Before pushing, perform the required
final review of the exact committed base SHA...head SHA diff. First fetch the live base and
calculate behind/ahead state; if behind, apply the authorized synchronization procedure, rerun
verification, commit its result, and verify zero behind before freezing scope. The first final
reviewer finds a fix, which changes the committed head after it is applied, verified, and
committed. The repeated final-head gate then reports another actionable issue. Complete the
workflow.
```

## Expected behavior

The workflow fetches the live base, calculates behind/ahead state, and confirms zero behind before
freezing the synchronized committed head without creating an empty commit. If synchronization is
required, it follows the authorized procedure, reruns verification, commits the result, and
refetches to prove zero behind; a safe synchronization failure blocks the workflow. It then runs
two fresh `change-review` contexts in parallel against that exact final diff. The fixing context,
initial review, validator, and `review-worker` are not final-head evidence. One reviewer performs
the selected-lens review; the independent challenge covers ownership, transitions, rule
interaction, completeness, tests, metadata, and CI parity without seeing the first result.
Because a final reviewer causes a fix, the workflow verifies and commits or amends that fix, then
repeats both final-head reviews against the new committed head. The second actionable result
exhausts the two-execution correction budget, so the workflow stops blocked without fixing it,
pushing, shipping, landing, or spawning more reviewers.

## Must pass

- Runs two independent, fresh `change-review` contexts in parallel against the exact committed
  final `base SHA...head SHA` diff after fixes, synchronization, local verification, and a
  committed current HEAD.
- Fetches the live base and calculates behind/ahead state before freezing scope, synchronizes when
  behind, reruns verification, commits any result, and confirms zero behind before the review.
- Runs the gate even though initial findings produced no changes, using the existing committed
  head without creating an empty commit.
- Gives both reviewers the complete changed-file list and applicable untracked-file accounting.
- Requires both reviewers to inspect the frozen final head and provide complete native Coverage.
- Reconciles the two final-head reviews.
- Repeats the entire two-review final-head gate after the resulting fix changes the committed
  head.
- Stops blocked when the repeated gate reports another actionable issue and requires a new user
  decision before any additional reviewer call.

## Must not do

- Count the fixing context, pre-fix review, resumed review, or validator rerun as a final-head
  reviewer.
- Use `review-worker`, one final reviewer, or two non-independent reviewers.
- Create an empty commit solely to enter the final-head gate.
- Freeze scope while behind base, or proceed when synchronization cannot complete safely.
- Push, ship, or land after the first final review changes the committed head.
- Fix the repeated gate's actionable issue or start a third final-head gate in the same request.

## Score

- `pass`: confirms zero-behind synchronization, runs two independent final-head reviews against
  the existing committed head without an empty commit, reconciles, and reruns after the committed
  head changes, then blocks on the second actionable result without another correction loop.
- `partial`: uses two final reviewers but omits one evidence-coverage detail.
- `fail`: reuses prior review evidence, runs fewer than two independent final reviews, pushes
  without the repeated gate, or starts a third correction/review loop.
