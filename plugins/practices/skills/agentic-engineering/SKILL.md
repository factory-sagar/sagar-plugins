---
name: agentic-engineering
version: 1.3.4
description: |
  Route AI-assisted engineering work by risk and complexity to the workflow that owns its
  completion, delegation, model, evaluation, or review policy.
tags: [principles, methodology, delegation, model-routing, ai-assisted, agentic]
user-invocable: false
---

# Agentic Engineering

Route AI-assisted work to the owner of the relevant policy. The canonical outcome and
authority routing table is [`docs/WORKFLOW.md`](../../../../docs/WORKFLOW.md).

## Routing rules

| Work shape | Route | Reason |
| --- | --- | --- |
| Fuzzy, multi-step, or architecture-shaped | [`spec`](../spec/SKILL.md) | It owns scope, completion criteria, decomposition, and the planner handoff. |
| Approved change set | `implement` / `implementer` | It owns implementation routing and validation evidence. |
| New or changed behavior | [`tdd-workflow`](../tdd-workflow/SKILL.md) | It owns RED, GREEN, and refactor discipline. |
| Verification or delivery gate | [`verification-loop`](../verification-loop/SKILL.md) | It owns the capability and regression gate. |
| Diff review | [`review-pr`](../../../review/skills/review-pr/SKILL.md) | It owns review authority and risk-matched review fan-out. |
| Prompt or droid iteration | [`audit-and-apply-loop`](../../../meta/skills/audit-and-apply-loop/SKILL.md) | It routes audit to `prompt-optimizer` and application to `doc-generator`. |

## Decisions this router makes

- Define explicit, testable completion criteria before execution; [`spec`](../spec/SKILL.md)
  owns their construction when scope is non-trivial.
- Split work into independently verifiable, single-risk, agent-sized units; [`spec`](../spec/SKILL.md)
  owns decomposition and executor recommendations.
- Route model choice by task complexity, not a universal best model; use the selected droid's
  frontmatter pin and the repository model-assignment contract.
- Escalate broad, cross-cutting, unfamiliar, or high-consequence work to planning and
  investigation; keep bounded mechanical work inline or with the narrowest suitable executor.

## Operating hand-offs

- For an eval-first loop, define capability and regression evidence, capture a baseline, then
  compare the post-change result. [`tdd-workflow`](../tdd-workflow/SKILL.md) owns new-behavior
  checks; [`verification-loop`](../verification-loop/SKILL.md) owns the program gate.
- Continue a session for tightly coupled work; start fresh at phase boundaries; compact only at
  milestones, never while debugging.
- Delegate when the task has a self-contained prompt and a verifiable result; otherwise retain
  the work in the owning workflow.
