---
name: review-pr
version: 1.7.0
description: |
  Review a PR, branch, commit, or staged change through the mandatory review policy and
  diff-selected risk lenses. Plain "review" is read-only; explicit approve, fix, comment,
  ship, and merge wording grants only the corresponding stronger authority.
---

# Review PR

Turn a short review request into a complete, language-agnostic review. The user supplies
intent; the workflow supplies the method.

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

Words that describe quality (`thorough`, `deep`, `security`) change review depth, not
authority. A plain review stays read-only no matter how serious the diff is.

Approval is separate authority. Approval routing recognizes only an imperative `approve` that
targets a `PR` or `pull request` in the same clause, such as `Approve PR 42`, `Approve this PR`,
`Can you approve PR 42?`, `Approve and merge PR 42`, or `Approve and land this PR`. Advice
questions such as `Should I approve PR 42?` or `Should we approve PR 42?`, and approval of a plan
or change, do not authorize or route to `review-pr`.
`merge`, `land`, `ship`, or "make merge-ready" wording never grants approval authority. If branch
protection requires approval and explicit approval was not authorized, report the PR as blocked
rather than self-approving.

`approve PR` with no other mutation wording is an approval-only mode: complete the normal
read-only review, then run the approval gate. It never edits, pushes, or merges. When explicit
approval appears with `comments`, `ship`, or `land`, run the approval gate only after that mode
has reached merge-ready.

## Prompt-depth routing

Classify the request before reviewing:

- **Short directive**: a target and action with little design context. Run the full review
  workflow directly. Short never means shallow.
- **Detailed execution request**: constraints or known risks are supplied. Add them to the
  review manifest as required concerns; do not replace the standard policy.
- **Design-shaped request**: asks whether the architecture, ownership, contract, or approach
  is right. Run `discovering-unknowns`, then `architecture-scan` or `tech-spec` before
  reviewing implementation details.
- **Failure-shaped request**: includes a regression, stack trace, or failing check. Run
  `debugger` first; review the resulting fix against the proven cause.

## Workflow

### 1. Resolve the target and authority

Resolve the PR, branch, commit range, named files, or staged diff. For PRs, fetch:

- metadata, base and head SHA, body, linked issue, and changed-file stats;
- inline review comments;
- review summary bodies;
- PR conversation comments;
- GraphQL review-thread IDs and resolution state.

Use the current repository checkout for every mode and never create a secondary checkout or
clone. In mutating modes, check out the PR branch natively in the current checkout.

Before switching branches, read `git config --bool --get workflow.disposableCheckout`:

- `true`: this checkout is explicitly disposable. Run `git reset --hard` and `git clean -fd`,
  then use `gh pr checkout <number> --force`.
- absent or `false`: require `git status --porcelain` to be empty. If it is not empty, stop and
  report the blocker; never stash, discard, move, or overwrite existing work.

Completion criterion: the exact base SHA, head SHA, diff, existing conversation, mode, and
working directory are known.

Capture `git status --porcelain` before reviewing. Classify each untracked path as:

- present before the implementation program and user-owned;
- created by the program and reviewable;
- unknown, which remains in scope until ownership is proven.

### 2. Build the diff manifest

Classify tracked, staged, and untracked implementation paths plus diff content with the sibling
`select-review-lenses.mjs` script. Write changed paths and the unified diff to temporary
files, then run:

```bash
node <skill-dir>/select-review-lenses.mjs \
  --paths-file <changed-paths> --diff-file <unified-diff>
```

Every review receives the mandatory lenses. The selector adds risk lenses from evidence,
not programming-language identity. A React component receives UI-state lenses because of
the APIs it uses; another framework receives equivalent lenses when its signals appear.

The selector returns a `policySection` heading for every lens. Use `Grep` to locate each
heading in `review-policy.md`, then `Read` only that section through the next H2 heading.
Load the mandatory section plus the selected sections.

Completion criterion: each changed responsibility is covered by a mandatory or selected
lens, with a recorded signal explaining every selected lens.

### 3. Establish intent and conventions

Reconstruct what the change is meant to accomplish from the PR, linked issue, approved
program, tests, conversation, and surrounding code. Discover the target repository's
conventions and canonical validation commands.

When an approved program exists, create a coverage ledger with one row per unit:

| Unit | Expected paths/behavior | Actual paths | Targeted validation | Evidence |
| --- | --- | --- | --- | --- |

Read governing `AGENTS.md`, README, manifest, or registry files for every changed directory.
Build a CI-parity matrix from required workflow jobs and note which local command proves each
job or why it is remote-only. Run every safe local command and record its exit status. A
missing result or remote-only reason leaves the matrix incomplete and blocks a clean
assessment.

If implementation and stated intent disagree, treat intent as unresolved evidence, not as
permission to rationalize the code.

Completion criterion: expected behavior, changed contracts, repository conventions, and
the validation plan are explicit.

### 4. Review

`review-pr` owns all reviewer fan-out. Run `change-review` on every review and add `security`
whenever any selected lens has `reviewer: security`; no sibling workflow launches those reviewers
directly. For broad or high-consequence report or approve reviews, read `deep-review.md` and use
its independent passes over the shared notes format, then reconcile them. For broad or
high-consequence mutating reviews, final round 1 is the independent broad mutating review on the
frozen head, without a preliminary deep pair for that same head.

Every `change-review` Task description, and every budgeted `security` Task description, starts
with exactly one stage tag:

- `[review:standard]` for a single ordinary `change-review` pass;
- `[review:standard:retry]` for its one evidence-completion retry;
- `[review:standard:security]` for the `[security:selected]` risk-selected security pass, plus
  `[review:standard:retry:security]` for its one evidence-completion retry;
- `[review:deep:primary]` and `[review:deep:challenge]` for independent non-final deep
  `change-review` passes, plus `[review:deep:security]` for `[security:selected]` deep security
  and `[review:deep:retry:security]` for its one evidence-completion retry;
- `[review:final:<round>:primary]` and `[review:final:<round>:challenge]` for the two frozen-head
  reviewers, plus `[review:final:<round>:security]` when `[security:selected]` security is
  selected. Final round 1 permits `[review:final:1:retry:security]` for that pass's one
  evidence-completion retry; final round 2 is decision-only and permits no security retry. In all
  cases, `<round>` is `1` or `2`.

The guardrails plugin enforces these tags when installed. Never disguise a frozen/current/final
head review as `standard` or `deep`, and never reuse a final-head slot.

### Semantic task gate

Transport success is not review success. Apply semantic acceptance by reviewer type:

- `review-worker` must return `Status`, `Blockers`, and `Evidence Coverage`. It is complete only
  when Status is `complete` and Blockers are `none`. Initial Review must evidence that `Review
  Context` was written. Model-driven and convention passes must evidence their assigned
  lens/codepaths or pattern coverage, respectively. The final filter must evidence its persisted
  `Filter Status` coverage. `Status: blocked` always means the pass execution is incomplete and
  triggers the retry-or-block path.
- `change-review` is complete when its native `Assessment` and native `Coverage` are present,
  and Coverage is complete for selected lenses, changed files, substantial codepaths, and
  applicable untracked-file accounting. `Assessment: blocked` is a completed review outcome when
  Coverage is complete; reconcile its blocking findings.
- `security` is complete when its native `Assessment` and native `Coverage` are present, Coverage
  is complete for its scoped review, and caveats are explicit. `Assessment: blocked` is a
  completed review outcome when those requirements are met; reconcile its blocking findings.

Retry once only for a refusal, inability to complete the pass, missing required native fields, or
incomplete evidence. A `[security:selected]` standard, deep, or final-round-one security pass
uses its stage-specific security retry tag above; final round two remains decision-only and never
retries. If the retry remains incomplete, stop the workflow and report it blocked; do not ship or
land. The `review-worker` contract does not apply to `change-review` or `security`.

Every reviewer prompt must include the tracked diff scope and the explicit absolute path list
for program-created untracked files. Require each untracked file to be read and entered in the
changed-file accounting table; a normal git diff is not sufficient evidence for untracked
content.

A change is broad or high-consequence when any of these hold: more than 10 changed files,
more than 3 approved units, externally controlled state, multi-phase transitions, migrations,
authorization, concurrency, or 3 or more selected risk lenses. Deep review is mandatory in
those cases for report and approve modes. In mutating modes, the final-head gate's frozen-head
round-1 primary/challenge pair, plus stage-matched security when selected, supplies that
independent broad review instead; do not also run a preliminary deep pair for the same head.

Deep review requires at least two independent reviewer contexts:

1. the primary reviewer executes the full pass state machine;
2. a fresh challenge reviewer reads the full diff and runs the mandatory ownership,
   transition, rule-interaction, and completeness concerns without seeing the primary
   findings.

Reconcile the union. A resumed pass or comprehensive fallback inside the primary review does
not count as independent evidence.

Each selected lens must produce either:

- an evidenced finding with `path:line`, mechanism, impact, and correction direction; or
- a concrete verified-clean statement naming what was traced.

The selector's `evidenceRequirements` are mandatory, not advisory. In particular, a selected
`ui-state-reactivity` lens is incomplete unless its evidence names the real initiating owner and
programmatic writers, follows retained state through the terminal transition event, and proves
the winning rule where selectors or declarative policies overlap. Mock-only callback invocation
does not satisfy this evidence.

Maintain a review evidence ledger:

| Lens | Changed codepaths inspected | Finding or verified-clean evidence | Validator |
| --- | --- | --- | --- |

Reject a reviewer result that says "clean" without filling every selected-lens row and every
substantial changed codepath. Resume the reviewer with the missing rows or run an independent
pass; never translate an incomplete reviewer return into a clean assessment.

Review tests as evidence, not truth. Trace the behavior the tests claim to protect.

Completion criterion: every selected lens, approved program unit, governing metadata claim,
and substantial changed codepath has evidence; every finding is reachable, introduced by the
reviewed scope, actionable, and confidence-labeled.

### Final-head gate for broad or high-consequence mutating reviews

For every broad or high-consequence review in `fix`, `comments`, `ship`, or `land` mode, run this
gate before any push. It requires a clean, verified, synchronized, committed current HEAD, but
does not require initial findings to create a fix commit. Commit review fixes when they exist; if
there are no changes, use the existing committed current HEAD. Never create an empty commit.

1. Before freezing scope, fetch the live base ref and calculate
   `origin/<base>...HEAD` behind/ahead state. If behind, apply the active workflow's authorized
   base-synchronization procedure. Rerun full local verification and commit any synchronization
   result. Fetch the live base again and verify zero behind before freezing the exact base SHA
   and committed local head SHA. If synchronization cannot complete safely, stop as blocked.
   Then record the exact `base SHA...head SHA` diff, complete changed-file list, and applicable
   untracked-file accounting.
2. Spawn **two fresh `change-review` Task contexts in parallel** against that same exact
   committed diff. In the first execution, prefix their descriptions with
   `[review:final:1:primary]` and `[review:final:1:challenge]`; if a head-changing correction
   requires the repeated execution, use `[review:final:2:primary]` and
   `[review:final:2:challenge]`. Do not use `review-worker` for this gate. The primary performs
   the full selected-lens final review. The challenge focuses on ownership, transitions, rule
   interaction, completeness, tests, metadata, and CI parity without seeing the first result.
   When security is selected, spawn one fresh, independent
   `[review:final:<round>:security] [security:selected]` context in the same round. Give every
   final-round reviewer the complete changed-file list and applicable untracked-file accounting.
3. Require both `change-review` contexts, plus stage-matched security when selected, to inspect
   the frozen final head and satisfy their respective semantic acceptance and selected-lens
   evidence coverage.
4. Reconcile both final-head results into one finding set.

If final round 1 reconciliation produces an in-scope fix, apply it, run targeted verification for
the correction plus one fresh integration gate for the new head, and commit the fix. Freeze the
new base and committed head SHAs, then run round 2 against the new head. A final-head gate passes
only when all required independent final reviewers are complete, evidence-covered, reconciled,
and no resulting fix changes the committed local head. Record that head as `finalReviewedHeadSha`
and carry it through every push and ship handoff. `fix` mode stops with that final reviewed local
commit. `comments`, `ship`, and `land` may push only after the gate passes.

**Correction budget:** execute the final-head gate at most twice per user request. The first
execution may produce one head-changing correction and one repeated gate. Final round 2 is
decision-only: if it produces any actionable finding, block before any edit and before any retry
or further review call, report the remaining findings, and require a new user decision to
continue.

### 5. Reconcile

Deduplicate findings by root cause and fix locus. Classify every candidate before applying it:

- **in-scope fix** — the smallest correction needed to satisfy approved intent or restore a
  pre-existing contract changed by this diff;
- **scope-expanding proposal** — a new subsystem, workflow, migration, backfill, rollback
  mechanism, compatibility layer, dependency, or product behavior not authorized by the
  approved request;
- **invalid / pre-existing** — speculative, intentional, test-disproved, unreachable, or not
  introduced by the reviewed scope.

Apply only in-scope fixes. Reject invalid/pre-existing candidates. A valid defect with only
scope-expanding remedies is not authorization for that remedy: stop before editing, explain the
concrete risk and smallest known options, and require a new user decision. Do not let severity
labels silently grant scope authority, turn product choices into automatic code changes, or let a
fix for one finding create an unapproved architecture program.

Order surviving findings by consequence:

1. data loss, authorization, secret exposure, or common-path failure;
2. broken contracts, state corruption, races, and migration hazards;
3. missing regression protection and operational blind spots;
4. maintainability regressions that materially raise future change risk.

Completion criterion: one canonical finding exists per defect, with no inflated duplicates.

### 6. Complete the authorized mode

- **report**: return findings and coverage. Perform no mutation.
- **approve**: complete **report**, then run the approval gate. Do not edit, push, or merge.
- **fix**: apply valid findings, run affected checks followed by the repository's canonical
  milestone gate, commit locally, pass the final-head gate when required, and stop.
- **comments**: read and follow `fix-comments.md`, then push and watch CI.
- **ship**: follow `ship` from preflight through merge-ready.
- **land**: pass the landing gate in `deep-review.md` Step 9, then merge.

Completion criterion: the workflow reaches exactly the authorized end state and no stronger
one.

### Approval gate

Run this gate only when the original request uses explicit approval authority. Capture the
`reviewedHeadSha` from the PR's `headRefOid` after the normal review completes. For explicit
approval combined with `comments`, `ship`, or `land`, wait until that mode is merge-ready, fetch
the final live `headRefOid`, and compare it with the last `reviewedHeadSha`. If they differ,
rerun the normal review against that exact final head and capture it as `reviewedHeadSha`.
Approval requires a reviewed final head; a prior different-head review never substitutes for it.

Before the final live-head comparison, verify against the live PR:

1. The review has no unresolved findings and the PR has zero unresolved review threads.
2. Required CI is green for the current head SHA.
3. The PR body is current for that head and still describes the PR.
4. The PR author's `author.login` differs from the authenticated current user. Determine the
   current user with `gh api user --jq .login`; do not infer self-authorship from bot status.

If any of these gates fails, report approval as blocked and do not approve. As the final API
operation immediately before approval, re-fetch the live `headRefOid` and require it to equal
`reviewedHeadSha`, with no intervening tool or API call. If it changed, block approval pending a
normal review of that exact new head; capture its reviewed SHA and restart the approval gate.
Otherwise, the next operation is:

```bash
gh pr review <url> --approve --body "Review complete, required checks are green, and the PR is merge-ready."
```

For `approve` mode, stop after this command. Approval remains additive permission and never
implies push or merge authority.

## Output

```markdown
## Review

**Mode:** <report | approve | fix | comments | ship | land>
**Target:** <base SHA>...<head SHA>
**Assessment:** <correct | needs changes | blocked | merge-ready | merged>

### Selected lenses
- <lens> — <signal>

### Findings
- [P<n>·<confidence>] <title> — `path:line`
  - Mechanism:
  - Impact:
  - Correction:

### Coverage
- Files read:
- Behavior traced:
- Program units: <covered / missing>
- Lens evidence: <complete / missing rows>
- Governing metadata:
- CI-parity matrix:
- Validators:
- Existing comments: <found / replied / resolved / remaining>
- Reviewer returns: <complete / blocked; type-aware acceptance and coverage>
- CI at head SHA:
- PR body at head SHA:

### Deviations
<entries or `none`>
```

An empty findings section says `No material issues found.` It never invents a nit to prove
that review happened.
