---
name: tdd-workflow
description: Test-driven development workflow with red-green-refactor discipline, coverage targets, and Git checkpoints. Use when writing new features, fixing bugs, refactoring, or adding API endpoints — anywhere new behavior is being introduced or behavior is changing. Triggers on "TDD", "write tests first", "test-driven", "RED-GREEN-REFACTOR", "fix bug", "add feature".
---

# TDD Workflow

Enforce test-first development for every behavior change: write a failing test, make it pass with the smallest possible implementation, then refactor.

## When to Activate

- Writing new features or functionality.
- Fixing bugs (write the test that reproduces the bug first).
- Refactoring code that has incomplete coverage.
- Adding API endpoints or new public surface.
- Implementing a unit that came out of the `spec` decomposition.

## When NOT to Activate

- Pure docs or config changes (no behavior to test).
- Spike / throwaway exploration where the code will be deleted (note: most "throwaway" code survives — be honest about the scope).
- Tests are already in place AND the change is purely internal refactor with no behavior change (verify by running the suite — it should stay green throughout).

## Core Principles

### 1. Tests BEFORE Code
Always write the test first. The test fails (RED), then implementation makes it pass (GREEN), then optionally refactor.

### 2. Coverage Requirements
- **Minimum 80% line + branch coverage** for the changed code.
- All edge cases covered (empty input, max input, null/undefined, error path).
- Boundary conditions verified (off-by-one, first/last element, threshold values).
- Error scenarios tested explicitly.

### 3. Test Pyramid

| Test type | Scope | Speed | Tools (typical) |
|---|---|---|---|
| **Unit** | Single function / pure logic / utility | ms | jest, vitest, pytest, go test, cargo test |
| **Integration** | API endpoints, DB ops, service interactions | 100s of ms | supertest, pytest with httpx, go test with httptest |
| **E2E** | Full user flow through real surface | seconds | playwright, cypress, selenium |

Aim for many unit, fewer integration, fewest E2E. E2E covers critical paths; unit covers everything.

## Procedure

### Step 1 — Write the user journey or behavior statement

State what behavior you're adding in user-facing terms.

```
As a <role>, I want to <action>, so that <benefit>.
```

Or for non-user-facing code: `Given <state>, when <event>, then <outcome>.`

### Step 2 — Write failing test cases

Cover the happy path, edge cases, and error paths. Use `describe` / `it` (or your framework's equivalent) to group them.

```
describe('feature X', () => {
  it('happy path: returns Y for input Z', () => { ... })
  it('edge: empty input returns []', () => { ... })
  it('edge: null input throws InvalidInputError', () => { ... })
  it('boundary: input at max length succeeds', () => { ... })
  it('boundary: input over max length rejects', () => { ... })
})
```

Run the tests. **Confirm they fail** for the right reason (assertion failure, not a syntax error or unrelated crash). If a test passes immediately, you wrote a tautology — delete it and write a real one.

### Step 3 — RED checkpoint commit

If under Git, commit the failing tests with a message that names the stage and the validated state:

```
test(<scope>): add failing tests for <behavior>
RED: <N> tests failing as expected
```

Do not squash this commit until the workflow is complete. The RED commit is evidence that the tests fail without the implementation.

### Step 4 — Implement the minimum to make tests pass

Write the **simplest possible implementation** that turns RED → GREEN. Avoid premature abstraction. The goal is "tests pass", not "production-quality code".

Run the suite. **Confirm only the new tests now pass** (and nothing else broke).

### Step 5 — GREEN checkpoint commit

```
feat(<scope>): minimal implementation for <behavior>
GREEN: <N> tests passing, no regressions
```

### Step 6 — Refactor (if needed)

Now that you have a passing test as a safety net, refactor for clarity, structure, and code smells. The suite must stay GREEN throughout.

Refactor signals:
- duplication (extract function / module)
- long functions (split by step)
- unclear names (rename)
- mixed concerns (separate)
- magic numbers (named constants)

Don't refactor what isn't covered. Refactoring without a test is "rewriting".

### Step 7 — REFACTOR checkpoint commit (optional)

```
refactor(<scope>): <what>
GREEN: all tests still passing
```

## Git Checkpoint Rules

- Each checkpoint commit lives on the current branch and the active task line.
- Do not treat earlier unrelated commits as substitutes for the RED/GREEN commits of the current task.
- The compact-form workflow is acceptable: 1 commit for RED, 1 commit for GREEN, 1 optional commit for REFACTOR. You don't need a separate "evidence-only" commit if RED/GREEN labels in the message are clear.
- Verify each checkpoint is reachable from `HEAD` on the active branch before relying on it as evidence.

## After the Loop

Once GREEN and clean:
1. Run `verification-loop` (build / typecheck / lint / suite with coverage). Address gaps.
2. Hand the diff to `change-review` for the merge gate.
3. If the change is security-sensitive, also hand to `security`.
4. Use `pr-describer` to synthesize the PR body from the same diff.
5. Use `commit-message-writer` if your final squash-commit message needs polish.

## Companion Skills

- `spec` — generates the unit you're now implementing.
- `verification-loop` — quality gate after the TDD loop.
- `coding-standards` — language-agnostic quality baseline for the implementation.
- `agentic-engineering` — operating principles (TDD enforces principle 4).

## Anti-Patterns

- **Writing implementation first, then tests** ("write tests when I have time"). The test-after-the-fact almost always tests the implementation, not the behavior.
- **Tests that don't fail before the implementation lands.** A test that passes immediately is testing nothing — it's a tautology or it's testing existing code.
- **Asserting on implementation details.** Tests should assert on observable behavior (outputs, side effects, state changes), not internal call sequences (unless the call IS the contract).
- **Skipping the RED state because the test "obviously" works.** No. Run it. Watch it fail. Then implement.
- **Mocking everything.** Heavy mocks → tests assert that the mocks were called correctly, not that the system works. Prefer real units; mock only at boundaries.
- **Coverage as the goal.** Coverage is a floor, not a ceiling. 100% coverage with weak assertions is worse than 70% with strong ones.
- **One test file per source file as a rule.** Group tests by behavior, not by file structure.

## Edge Cases

- **Bug fix with existing failing test you discovered:** RED is already established; commit the test under your branch first to anchor the regression, then GREEN with the fix.
- **Behavior change (not addition):** modify the existing test to match the new expectation FIRST, watch it fail, then change implementation.
- **Refactor with full coverage already:** no RED/GREEN; the "test" is "the existing suite stays green". Run before, run after, commit if green.
- **Code that's hard to test (filesystem, network, time):** introduce a seam (interface / dependency injection) before TDD, not as part of TDD. The seam itself can be a separate unit.
- **Legacy code with zero coverage:** characterization tests first (capture current behavior), then refactor under the safety net, then add behavior change.
- **Performance optimization:** the test asserts on correctness; the benchmark asserts on performance. Both should exist; only the test runs in CI on every commit.
