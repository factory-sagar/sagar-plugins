---
name: verification-loop
version: 1.5.1
description: |
  Verification policy for completed changes. Discovers repository gates, runs affected checks
  for fast feedback and the canonical milestone gate before hand-off, distinguishes introduced
  failures from baseline debt, and records exact evidence.
tags: [quality-gates, verification, testing, ci, build, lint, type-check]
user-invocable: false
---

# Verification Loop

Establish whether a completed change is gate-ready through repository-defined evidence. Success
means the result records each applicable phase, separates introduced failures from baseline debt,
and gives the next owner an exact hand-off. Use after a non-trivial completed change, before a
PR, after `tdd-workflow`, or when asked for readiness checks. Load
`../coding-standards/SKILL.md` and
`../coding-standards/TESTING_AND_VERIFICATION.md`, plus the relevant contract, async, or
observability standards.

## Discover the gate

Treat manifests and task files, CI configuration, and development documentation as evidence, in
that order of authority. Record each exact command and exit status. If a phase has no declared
tooling, report `n/a (no tooling detected)`; an inferred framework command must be labeled
inferred.

For prompt, plugin, configuration, or documentation changes, run applicable static checks even
without a build: parse changed JSON and YAML, check Markdown links and `git diff --check`, and
validate manifest discovery/counts. Execute these checks and record their exit statuses even when
the tree looks clean or empty; a clean `git diff --check` exit `0` is verification evidence, not a
reason to skip execution.

## Run applicable phases

Reuse valid validated evidence for the current change scope. Each independently changed unit
needs its targeted evidence; then run one integration gate for the program head.

| Phase | Pass condition | Failure handling |
| --- | --- | --- |
| Build | Exact build command exits `0`. | Stop and fix an introduced failure. |
| Type check | No type errors introduced by this change. | Block introduced errors; record pre-existing errors separately. |
| Lint | No remaining applicable violations. | Fix or justify violations; keep auto-fixes separate from semantic changes. |
| Tests | No introduced failures; changed-code coverage and skipped-test policy meet repository rules. When the repository has no coverage tooling, report changed-file coverage as `n/a (no coverage tooling)` rather than omitting it. | Block introduced failures, coverage regressions, and unjustified new skips. |
| Canonical gate | The discovered repository command exits `0` at the program head. | Stop; do not substitute a convenient partial aggregate. |

Run fast checks inline; delegate slow or noisy read-only commands to a `worker`, but verify its
reported exit status. Scope commands to changed packages when supported. A missing build or
type-checker is `n/a`; a missing test suite is a finding, not a green test phase. Missing tooling
is always `n/a (no tooling detected)`, never `blocked`: reserve `blocked` for a command that
exists but cannot run here, reported with its prerequisites.

## Baselines and hand-off

Classify every failure against a baseline. A failure introduced or surfaced by this change blocks
until fixed. Pre-existing baseline debt does not block this change, but report its command,
evidence, and affected scope. Never call a phase green merely because an existing failure is
elsewhere.

When applicable phases and the program-head integration gate pass, the change is gate-ready, not
merge-ready. Hand review ownership to `review-pr`; it alone decides and launches correctness or
security review fan-out. Name that hand-off in every report, whichever recommendation it carries.

## Boundaries

- Use a narrower workflow mid-debug and for prose-only changes with no prompt, manifest, config,
  generated-artifact, or plugin-discovery effect.
- Discover commands from repository evidence; never assume them. The repository's canonical gate
  is its documented or CI-used umbrella command, not a name guessed from another repository.
- A convenience aggregate such as `verify:quick` is not evidence that its standalone validators
  ran: inspect what it invokes and run each applicable standalone validator or report it
  unverified.
- Ratchet and freeze gates are required; never raise a baseline to pass.
- Run one integration gate for the program head and avoid repeating equivalent validators or the
  canonical gate per unit.
- `review-pr` alone decides and launches correctness or security review fan-out; this skill never
  launches those reviewers directly.

## Report

```markdown
## Verification Results
| Phase | Status | Command and evidence |
| --- | --- | --- |
| Build | pass / fail / n/a / blocked | `<command>`; exit `<status>`; <scope> |
| Type-check | pass / fail / n/a / blocked | `<command>`; exit `<status>`; <introduced vs baseline> |
| Lint | pass / fail / n/a / blocked | `<command>`; exit `<status>`; <scope> |
| Tests | pass / fail / n/a / blocked | `<command>`; exit `<status>`; <coverage/skips> |
| Canonical gate | pass / fail / n/a / blocked | `<command>`; exit `<status>` |

## Pre-existing issues spotted (not blocking this change)
- <baseline evidence and scope>

## Recommendation
- Green-light: gate-ready; hand review ownership to `review-pr`.
- Fix first: <introduced failure or blocked prerequisite>.
```