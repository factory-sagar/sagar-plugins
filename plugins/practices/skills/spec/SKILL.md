---
name: spec
version: 1.6.0
description: |
  Plan non-trivial features, refactors, and migrations. Converts short or detailed requests
  into evidence-backed decisions, testable acceptance criteria, and executable units; adds
  unknown-discovery and technical architecture automatically when the request demands them.
tags: [planning, decomposition, scoping, workflow, spec]
---

# Spec: Plan and Decompose

Produce a definition of done and an executable decomposition. Success means the user can approve
it whole, challenge a decision, or delegate any unit directly. Canonical workflow routing lives
in [`docs/WORKFLOW.md`](../../../../docs/WORKFLOW.md).

Load `../coding-standards/SKILL.md` and only topic documents relevant to the request. Use
`tech-spec` for typed contracts, seams, call stacks, or design alternatives; use
`architecture-scan` before choosing a refactor target or code location; use `grilling` when a
material decision lacks context.

## Boundaries

- Keep cross-workflow routing in [`docs/WORKFLOW.md`](../../../../docs/WORKFLOW.md); do not
  duplicate its routing table.
- Put a constraint the user did not state in Open Questions rather than inventing it.
- Use only existing delegates from the Delegation Map; do not invent a droid.

## Method

1. Restate the outcome, non-goals, stated constraints, and ambiguity. Ask one focused question
   only when an answer cannot be established from supplied context or repository evidence.
2. Establish a system anchor for non-trivial or unfamiliar work. Use `planner` by default for
   multi-file, multi-unit, or unfamiliar scope; use the built-in `explorer` for small unfamiliar
   scope, `deep-understanding` for subsystem questions, and `deep-research` for external facts.
   Cite the resulting paths and source. Reuse delegated evidence gathering.
3. Write the spec, preserving user constraints and recording unstated constraints as Open
   Questions.
4. Decompose, sequence dependencies, identify independent work, and name one delegate per unit.
   Include risk, rollback, and the next action.

A testable acceptance criterion lets a teammate write a test: “make it fast” fails; “renders the
dashboard in <500 ms p95 with 1,000 rows on an M2 MacBook Pro” passes. An out-of-scope item is a
reasonable reader's likely assumption that you explicitly decline, not an absurdity.

## Spec output

```md
## Spec

**Goal:** <one-sentence outcome>

**Acceptance criteria:**
- <observable, testable result>

**Out of scope:**
- <reasonable interpretation explicitly declined, with reason>

**Constraints:**
- <stated runtime, dependency, security, performance, deadline, or compliance constraint>

**System anchor:**
- <relevant repository fact with path:line>
- Source: <droid or repository source>

**Open questions:**
- <unresolved decision or unstated constraint>
```

Emit the complete spec and decomposition as your final message. In headless runs the reader
sees only the final message; a summary of content "delivered above" scores as missing.

## Decomposition

Apply the **15-minute unit rule**. Every unit is independently verifiable, has one dominant risk,
and has a clear done condition. Split implementation work expected to exceed 15 focused minutes;
merge a one-line unit such as a variable rename into an adjacent unit. If work exceeds 12 units,
consolidate shared work or split the spec.

```md
## Decomposition

| # | Unit | Done condition | Delegate to | Reason |
|---|------|----------------|-------------|--------|
| 1 | <verb phrase> | <observable signal> | <droid-name, `worker`, or `<self>`> | <why> |

## Sequence
1. <unit and dependency>

## Parallelization opportunities
- <independent units or ordering constraint>

## Risk
- **Highest-risk unit:** <number and reason>
- **Rollback plan:** <reversal>
- **Verification gate:** `verification-loop`, then `review-pr`, before PR shaping.

## Hand-off after spec
<concrete next action and delegate — name the full closing chain: `pr-describer` for the PR
body and `commit-message-writer` for the commit, after `verification-loop` and `review-pr` pass>
```

## Delegation Map

| Unit shape | Delegate | Why |
|---|---|---|
| Unfamiliar repository shape or entry points | `explorer` | Fast repo triage |
| Architecture or agentic-config understanding | `deep-understanding` | Evidence-anchored investigation |
| External library, CVE, or best-practice research | `deep-research` | Source-backed external research |
| Approved change set or debugger fix plan | `implementer` | Minimal changes with targeted verification |
| Untested behavior or TDD RED test | `test-engineer` | Risk-ordered test coverage |
| Root-cause analysis before a fix | `debugger` | Evidence-ranked diagnosis |
| Open-ended implementation | `worker` | General-purpose execution with supplied context |
| TDD implementation | `worker` with `tdd-workflow` | Test-first implementation |
| Quality gates | `<self>` with `verification-loop` | Mechanical validation |
| Pre-merge review and security depth | `review-pr` | Owns review fan-out and stage selection |
| PR description | `pr-describer` | Structured PR body |
| Conventional Commit message | `commit-message-writer` | Format-mechanical synthesis |
| Droid or skill prompt iteration | `audit-and-apply-loop` | Audit-apply-verify cycle |
| Apply agentic-config audit findings | `doc-generator` | Marketplace editing owner |
| Procedural planning step | `<self>` | No delegation needed |

If no entry fits, use `worker` with a self-contained prompt.

## Edge cases

- **Small request:** state that a full spec is unnecessary; return one or two units if useful.
- **Too large for one pass:** produce a milestone-level spec whose criteria are milestone goals,
  then recurse with this skill for each milestone; apply the 15-minute rule within each milestone.
- **Research question or bug report:** start with `deep-research` or `deep-understanding`; for a
  bug, investigation is the first unit and the spec follows the evidence.
- **Multiple repositories or services:** name them in Constraints; decompose per repository and
  state cross-service ordering or deployment coupling under Risk.
- **User-supplied spec:** validate observable criteria, explicit scope, and constraints; annotate
  gaps and decompose it while preserving the supplied specification.
- **No suitable delegate:** use `worker` with a self-contained prompt.
