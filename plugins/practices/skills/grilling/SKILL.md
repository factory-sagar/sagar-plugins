---
name: grilling
version: 1.0.0
description: |
  Interview the user relentlessly about a plan or design. Use when the user wants to stress-test a
  plan before building, or uses any "grill" trigger phrases.
tags: [planning, interview, design, critique, discovery]
---

# Grilling

Interview the user relentlessly about every aspect of the plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one by one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing. Asking multiple questions at once is bewildering. One question means one actual ask with one missing fact: the question line contains exactly one question mark and does not contain " and " or " or ". Do not append secondary asks, shopping lists, repo-path requests, stack-constraint lists, or "also tell me" bullets in the same turn.

If a question can be answered by exploring the codebase, explore the codebase instead.

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

Do not write a full spec or implementation plan inside this skill unless the user asks after the grilling summary.
