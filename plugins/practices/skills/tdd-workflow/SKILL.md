---
name: tdd-workflow
version: 1.5.0
description: |
  Test-first execution policy for new or changed behavior: prove RED through the real seam,
  implement the smallest GREEN change, refactor only under the regression net, and preserve
  repository-defined validation evidence.
tags: [testing, tdd, workflow, quality, red-green-refactor, coverage]
user-invocable: false
---

# TDD Workflow

Use for new or changed behavior, bug fixes, public surfaces, and refactors without adequate
coverage. Do not use it for prose, mechanical changes with verified coverage, or throwaway
experiments. Load `../coding-standards/SKILL.md` and
`../coding-standards/TESTING_AND_VERIFICATION.md`; load the relevant standards topic when
modules, async ownership, contracts, or observability change.

## Loop

Work one observable behavior slice at a time. State it as `Given <precondition>, when <event>,
then <outcome>`. At RED/GREEN/refactor checkpoints, use the selected targeted command rather than a broad suite.
Run one targeted test or validator per unit independently changed; reserve
the full suite or integration gate for program completion.

| Checkpoint | Required action | Evidence |
| --- | --- | --- |
| RED | Write the next test before production code and run it through the real behavior seam. | It fails for the intended assertion or contract reason before implementation begins. A mock-satisfied test is not proof. |
| GREEN | Change only the least code needed to turn that test green. Do not modify the test or add unasserted behavior. | The selected targeted test or validator passes. |
| REFACTOR | Improve only an identified smell after GREEN. | The selected targeted test or validator remains green after every change. |

Test observable outcomes, including applicable boundaries and error behavior, rather than
internal call sequences. Use real units; isolate only I/O boundaries. If the test passes at
RED, it is a tautology or tests existing behavior. If it fails for setup, syntax, or another
unrelated reason, repair the test before implementation. For legacy code, first add
characterization coverage. For an untestable dependency, first create a testable seam in its
own cycle.

## Execution

Delegate non-trivial test writing, implementation, and refactoring to `test-engineer` or
`implementer` when available, otherwise a scoped `worker`. Keep RED and GREEN separate: the
test-writing delegate must not implement, and the implementer must not change tests. The
orchestrator verifies the returned command result and minimality.

The implementation prompt must require the deviations contract: a minor territory contradiction
takes the conservative, reversible option and is logged with plan, repository evidence, choice,
and impact; a premise contradiction stops and reports. Never deviate silently.

Record RED before the implementation exists. Commit the failing test, or otherwise capture the
failing run, before writing production code: a single diff containing both a test and the code
that satisfies it is not RED evidence, because it cannot show implementation was absent.
Checkpoint commits identify the behavior and contain `RED: <N> failing as expected` or
`GREEN: targeted test or validator passing`. Do not treat unrelated commits as proof.

## Completion

GREEN makes a unit implementation-complete, not ship-ready. At program completion, run
`verification-loop` once for the repository gate, then hand review ownership to `review-pr`.
`review-pr` owns correctness and security reviewer fan-out; this skill does not launch
reviewers. Use `pr-describer` or `commit-message-writer` only after that workflow.