---
name: grilling
version: 1.3.0
description: |
  Stress-test a plan or design one architecture-changing question at a time. Invoke when
  unresolved product, ownership, boundary, or risk decisions would make implementation
  speculative.
tags: [planning, interview, design, critique, discovery]
user-invocable: false
---

# Grilling

Reach a shared understanding of the plan by resolving architecture-changing decisions one at a
time. Success means the next artifact has a concrete outcome, named constraints and non-goals,
and either a resolved riskiest decision or an explicit open question. Walk each branch of the
design tree in dependency order and provide a recommended answer for every question.

## Boundaries

- Ask exactly one actual question with one missing fact per turn; wait for feedback before the
  next question. Its question line contains exactly one question mark and does not contain
  " and " or " or ".
- Do not append secondary asks, shopping lists, repo-path requests, stack-constraint lists, or
  "also tell me" bullets in the same turn.
- Resolve facts answerable through codebase exploration from the repository instead of asking.
- Return the Grilling Summary before writing a full spec or implementation plan unless the user
  asks after the summary.

## Procedure

1. State the current plan or design in one sentence.
2. Identify the highest-leverage unresolved decision.
3. Ask exactly one question about that decision and include your recommended answer.
4. Wait for the user's response before asking another question.
5. Repeat until the core problem, users/callers, constraints, acceptance criteria, risks, and next artifact are clear.

## Stop Criteria

Stop grilling when all of these are true:

- The desired outcome is concrete enough for `spec` or `tech-spec`.
- Major constraints and non-goals are named.
- The riskiest open decision is either answered or explicitly marked as an open question.
- The next step is clear: `spec`, `tech-spec`, `architecture-scan`, implementation, or no action.

## Output When Done

When the interview is complete, return:

```md
## Grilling Summary

**Resolved decisions:**
- <decision and answer>

**Open questions:**
- <question, or `none`>

**Recommended next step:**
- <spec / tech-spec / architecture-scan / implementation / stop>
```
