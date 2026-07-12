---
name: implement
version: 1.3.0
description: |
  Build approved work. Routes explicit change sets to the implementer, new behavior through
  test-first execution, and small mechanical changes inline; every path records deviations
  and finishes with the repository's verification gate.
---

# Implement

Given a task (from the invocation arguments or the conversation), route it to the right
executor. If no task is in hand, ask for one.

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
5. After each return, inspect the actual diff and run the unit's validator from the parent
   session. Record the command, exit status, and changed paths before marking the unit done.
6. Run milestone gates at declared boundaries and the repository's canonical gate after the
   final unit.
7. Invoke `review-pr` only after every unit has evidence. The review must cover the complete
   program diff and every changed or untracked implementation file.

Never hand a multi-unit program to one implementer task. A subagent's completion report is
evidence to verify, not authority to mark the program complete.

## Deviations contract

In every path, carry the Deviations contract from the `discovering-unknowns` skill:

- Minor territory contradiction → take the conservative option and log the deviation.
- Premise contradiction → stop and report.
- Never deviate silently.

## Verification

Finish with the `verification-loop` skill (or the repo's master gate) and report
deviations alongside the changes.
