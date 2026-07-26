---
name: discovering-unknowns
version: 1.2.0
description: |
  Map the gap between the user's request and repository reality. Invoke for unfamiliar
  territory, taste-shaped criteria, blind spots, or worker hand-offs; returns evidence-backed
  unknowns and the shared deviations contract.
tags: [planning, unknowns, blindspot, interview, deviations, map-territory]
user-invocable: false
---

# Discovering Unknowns

Use before scoping unfamiliar territory, when acceptance criteria are taste-shaped, when the
user requests a blind-spot pass, before delegating a plan, or for a large-change comprehension
check. Skip small work in known territory. Use `grilling` for a full interview and an
investigation droid when the agent, rather than the operator, lacks repository context.

## Find the gap

Repository reality outranks generic practice. Search before claiming an unknown and cite
`file:line` evidence for every constraint, convention, historical decision, calibration
example, CI gate, or baseline. Report:

1. Territory constraints and adjacent conventions that bind the work.
2. Historical decisions, TODOs, or reverts that invalidate an obvious approach.
3. The strongest comparable implementation and what it establishes as good.
4. Two to four unresolved questions, ordered by architectural leverage, with a recommended
   answer. Do not implement until architecture-changing answers are resolved.

For known unknowns, ask one question at a time and no more than three inline; record answers as
resolved decisions in the plan. For recognize-on-sight criteria, present three or four genuinely
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

If none, report `Deviations: none.` Attach this contract to delegated prompts. An optional
three-to-five-question quiz after long work is a comprehension check, never a release gate.