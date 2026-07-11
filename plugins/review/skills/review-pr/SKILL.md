---
name: review-pr
version: 1.0.0
description: |
  Review a PR, branch, commit, or staged change through the mandatory review policy and
  diff-selected risk lenses. Plain "review" is read-only; "review and fix", "address
  comments", "ship", and "merge" opt into progressively stronger mutation authority.
---

# Review PR

Turn a short review request into a complete, language-agnostic review. The user supplies
intent; the workflow supplies the method.

## Authority modes

Choose the narrowest mode authorized by the user's words:

| User intent | Mode | Allowed end state |
| --- | --- | --- |
| `review PR <n>` | `report` | Findings only. No edits, comments, pushes, approvals, or merges. |
| `review and fix PR <n>` | `fix` | Fix valid findings, verify, commit locally, stop before push. |
| `address PR <n>` / `fix review comments` | `comments` | Triage every existing comment, fix, reply, resolve, push, and watch CI. |
| `ship` / `push and make merge-ready` | `ship` | Push, refresh the PR, watch CI, resolve threads, report merge-ready. |
| `merge PR <n>` | `land` | `ship`, then merge only after every hard gate passes. |

Words that describe quality (`thorough`, `deep`, `security`) change review depth, not
authority. A plain review stays read-only no matter how serious the diff is.

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

Use an isolated worktree for a remote PR whenever any mode beyond `report` may edit. Never
stash, discard, move, or overwrite unrelated work to enter a review branch.

Completion criterion: the exact base SHA, head SHA, diff, existing conversation, mode, and
working directory are known.

### 2. Build the diff manifest

Classify changed paths and diff content with the sibling
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

Reconstruct what the change is meant to accomplish from the PR, linked issue, tests,
conversation, and surrounding code. Discover the target repository's conventions and
canonical validation commands.

If implementation and stated intent disagree, treat intent as unresolved evidence, not as
permission to rationalize the code.

Completion criterion: expected behavior, changed contracts, repository conventions, and
the validation plan are explicit.

### 4. Review

Run `change-review` on every review. Add `security` whenever any selected lens has
`reviewer: security`. For broad or high-consequence changes, read `deep-review.md` and use
its independent passes over the shared notes format, then reconcile them.

Each selected lens must produce either:

- an evidenced finding with `path:line`, mechanism, impact, and correction direction; or
- a concrete verified-clean statement naming what was traced.

Review tests as evidence, not truth. Trace the behavior the tests claim to protect.

Completion criterion: every selected lens is accounted for and every finding is reachable,
introduced by the reviewed scope, actionable, and confidence-labeled.

### 5. Reconcile

Deduplicate findings by root cause and fix locus. Reject speculative, pre-existing,
intentional, or test-disproved candidates. Do not turn product choices into automatic code
changes.

Order surviving findings by consequence:

1. data loss, authorization, secret exposure, or common-path failure;
2. broken contracts, state corruption, races, and migration hazards;
3. missing regression protection and operational blind spots;
4. maintainability regressions that materially raise future change risk.

Completion criterion: one canonical finding exists per defect, with no inflated duplicates.

### 6. Complete the authorized mode

- **report**: return findings and coverage. Perform no mutation.
- **fix**: apply valid findings, run affected checks followed by the repository's canonical
  milestone gate, commit locally, and stop.
- **comments**: read and follow `fix-comments.md`, then push and watch CI.
- **ship**: follow `ship` from preflight through merge-ready.
- **land**: pass the four-point landing gate in `deep-review.md` Step 9, then merge.

Completion criterion: the workflow reaches exactly the authorized end state and no stronger
one.

## Output

```markdown
## Review

**Mode:** <report | fix | comments | ship | land>
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
- Validators:
- Existing comments: <found / replied / resolved / remaining>
- CI at head SHA:
- PR body at head SHA:

### Deviations
<entries or `none`>
```

An empty findings section says `No material issues found.` It never invents a nit to prove
that review happened.
