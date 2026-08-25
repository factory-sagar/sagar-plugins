---
name: implement
version: 1.4.0
description: |
  Build approved work. Routes explicit change sets to the implementer, new behavior through
  test-first execution, and small mechanical changes inline; every path records deviations
  and finishes with the repository's verification gate.
---

# Implement

Turn a task from the invocation arguments or conversation into an appropriately scoped,
verified implementation path. Success means approved changes reach the right executor, new
behavior follows test-first execution, small mechanical work stays bounded, and every completed
program reaches the repository's verification gate with recorded deviations. If no task is in
hand, ask for one.

## Routing

Route by what is in hand:

1. **An approved change set exists** (review findings, a spec unit with acceptance
   criteria, a debugger fix plan, an explicit fix list) — delegate to the `implementer`
   droid with the change set.
2. **New or changed behavior without an approved change set** — run the `tdd-workflow`
   skill (RED → GREEN → REFACTOR with checkpoint commits).
3. **Small mechanical change in known territory** — apply it inline.

## Program execution

When the approved artifact contains multiple ordered units, plans, work packages, or
milestones, the main agent remains the program manager:

1. Read the complete index and build the dependency graph.
2. Create one TodoWrite item per unit plus milestone validation and final review.
3. Delegate one independently verifiable unit per `implementer` task. Parallelize only units
   whose dependencies are complete and whose write sets are disjoint. All delegates operate
   in the current native checkout. Serialize units that could touch shared files.
4. Before each delegation, read that unit's source artifact and pass its exact scope,
   acceptance criteria, boundaries, and targeted validator.
5. Each independently changed unit runs exactly one targeted validator. The executor records
   reusable validation evidence in a ledger containing: scope/content identity, command, exit
   status, and changed paths. After each return, the parent inspects the actual diff and checks
   that evidence before marking the unit done; the parent must not repeat a full or canonical
   validator per unit.
6. After all units are integrated, run exactly one integration/master canonical gate at the
   program head, not per unit. Reuse same-scope valid evidence and run only the remaining
   program-head validation needed for the integration gate.
7. Invoke `review-pr` only after every unit has evidence and the integration gate completes.
   `review-pr` owns all review fan-out. The review must cover the complete
   program diff and every changed or untracked implementation file.

## Boundaries

- **One independently verifiable unit per `implementer` task.** Never hand a multi-unit program
  to one implementer task.
- **Completion evidence remains with the parent.** A subagent's completion report is evidence to
  verify, not authority to mark the program complete.

## Deviations contract

In every path, carry the Deviations contract from the `discovering-unknowns` skill:

- Minor territory contradiction → take the conservative option and log the deviation.
- Premise contradiction → stop and report.
- Record every deviation explicitly.

## Verification

After all units are integrated, finish with the single program-head integration/master gate
through the `verification-loop` skill (or the repo's master gate), reusing same-scope valid
validation evidence. Report deviations alongside the changes.
