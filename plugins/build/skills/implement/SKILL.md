---
name: implement
version: 1.0.0
description: |
  Route "implement this" to the right executor: an approved change set goes to the
  implementer droid, new or changed behavior without one runs tdd-workflow, and a small
  mechanical change in known territory is applied inline. Every path carries the
  Deviations contract and finishes with verification.
  Use when:
  - The user says "implement this", "/implement <task>", "apply this change set", "build this unit"
  - A spec unit, review finding set, debugger fix plan, or explicit fix list is ready to execute
  - New behavior needs implementing and the entry discipline (droid vs TDD vs inline) must be chosen
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

## Deviations contract

In every path, carry the Deviations contract from the `discovering-unknowns` skill:

- Minor territory contradiction → take the conservative option and log the deviation.
- Premise contradiction → stop and report.
- Never deviate silently.

## Verification

Finish with the `verification-loop` skill (or the repo's master gate) and report
deviations alongside the changes.
