# Reviewer Reply Contract

Normative definition of what a reviewer Task must return before its pass counts as executed.
Other review documents restate parts of this contract operationally; on conflict, this file
wins.

## Principle

Transport success is not review success. A Task call that returns cleanly but whose reply
lacks this contract is an incomplete pass, never an accepted review.

## Worker-native contract (`review-worker`)

Every `review-worker` return carries three fields:

- `Status: complete | blocked`
- `Blockers: none | <specific blockers and missing evidence>`
- `Evidence Coverage: <what was actually inspected>`

A pass is complete only when `Status: complete` and `Blockers: none`, and Evidence Coverage
proves the work of that pass type:

- Initial Review: evidences that `Review Context` was written.
- Model-driven passes: evidence the assigned lenses and codepaths.
- Convention passes: evidence the pattern checks and codepaths; a zero-count result is
  complete only when `Blockers: none` and Evidence Coverage explicitly lists every available
  convention source inspected and found inapplicable.
- Final filter: evidences persisted `Filter Status` coverage for every finding block
  filtered or kept.

`Status: blocked` always means the pass execution is incomplete and triggers the
retry-or-block path. Never represent a blocked pass as review evidence.

## Reviewer-native contract (`change-review`, `security`)

The worker-native fields do not apply to these reviewers. Each is complete when its native
`Assessment` and native `Coverage` are present and Coverage is complete for its scope:

- `change-review`: Coverage complete for selected lenses, changed files, substantial
  codepaths, and applicable untracked-file accounting.
- `security`: Coverage complete for its scoped review, with explicit caveats.

A native `Assessment: blocked` with complete Coverage is a completed review outcome, not a
failed pass: reconcile its blocking findings instead of retrying.

## Canonical Coverage rows

A blocked or incomplete outcome still emits the full report template and every canonical
Coverage row, using `n/a` with a reason where a row does not apply, and names each missing
native field exactly. Omitting a row is incomplete, not a valid abbreviated report.

## The single retry

Retry a reviewer exactly once, and only for: a refusal, inability to complete the pass,
missing required native fields, or incomplete evidence. The retry names the missing contract
exactly. Stage-tagged retries use their stage-specific slot (`[review:*:retry]` or
`[review:*:retry:*]`); every review stage permits exactly one. If the retry remains incomplete,
stop the workflow and report it blocked; do not ship, land, approve, or merge past a blocked
review.
