---
name: discovering-unknowns
version: 1.3.0
description: |
  Map the gap between the user's request and repository reality. Invoke for unfamiliar
  territory, taste-shaped criteria, blind spots, or worker hand-offs; returns evidence-backed
  unknowns and the shared deviations contract.
tags: [planning, unknowns, blindspot, interview, deviations, map-territory]
user-invocable: false
---

# Discovering Unknowns

Map the gap between a request and repository reality before unfamiliar or large-change work,
taste-shaped acceptance criteria, blind-spot passes, or plan delegation. Success means the
result identifies the evidence that binds the work, the highest-leverage unresolved choices, and
the shared deviations contract for its executors. Small work in known territory can proceed
without this pass. Use `grilling` for a full interview and an investigation droid when the
agent, rather than the operator, lacks repository context.

## Boundaries

- Resolve architecture-changing answers before implementation.
- Ask no more than three inline questions, one at a time, and record answers as resolved
  decisions in the plan.
- Attach the Deviations contract below to delegated prompts. An optional three-to-five-question
  quiz after long work is a comprehension check, never a release gate.

## Find the gap

Repository reality outranks generic practice. Search before claiming an unknown and cite
`file:line` evidence for every constraint, convention, historical decision, calibration
example, CI gate, or baseline. Report:

1. Territory constraints and adjacent conventions that bind the work.
2. Historical decisions, TODOs, or reverts that invalidate an obvious approach.
3. The strongest comparable implementation and what it establishes as good.
4. Two to four unresolved questions, ordered by architectural leverage, with a recommended
   answer.

For known unknowns, record answers as resolved decisions in the plan. For recognize-on-sight
criteria, present three or four genuinely
different, cheaply comparable variants with a tradeoff, then select one. Lead plans with
decisions most likely to change, not file order.

## Deviations contract

Every implementer carries this rule:

- A **minor contradiction**, where a detail is wrong but the goal stands, takes the
  conservative option: no unrequested product surface and easiest to revert. Log it and
  continue.
- A **premise contradiction**, where repository evidence invalidates the approach, stops and
  reports the evidence and proposed alternative. Do not silently pivot.

```md
## Deviations
- D1 — plan: <what the plan/finding/spec said>
  territory: <what the code actually showed — file:line evidence>
  chose: <the conservative option taken>
  impact: <behavior/scope effect, one line>
```

If none, report `Deviations: none.`