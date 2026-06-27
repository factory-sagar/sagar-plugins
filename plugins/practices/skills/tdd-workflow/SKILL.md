---
name: tdd-workflow
version: 1.0.0
description: |
  Test-driven development discipline with explicit RED-GREEN-REFACTOR phases, Git checkpoint commits
  per phase, 80%+ coverage targets across the unit/integration/E2E test pyramid, and explicit worker
  delegation for the implementation steps.
  Use when:
  - Writing new features or functionality
  - Fixing bugs (write the regression test that reproduces the bug FIRST)
  - Refactoring code that has incomplete coverage
  - Adding API endpoints or new public surface
  - Implementing a unit from a `spec` decomposition where new or changed behavior is involved
  - User says "TDD", "write tests first", "test-driven", "RED-GREEN-REFACTOR", "fix bug", "add feature"
tags: [testing, tdd, workflow, quality, red-green-refactor, coverage]
---

# TDD Workflow

Test-first discipline for every behavior change. The loop: write a failing test, watch it fail for the right reason, implement the smallest thing that makes it pass, then optionally refactor under the safety net.

This skill assumes the main agent is orchestrating the loop; the **actual test and implementation writing should be delegated to a `worker`** (Factory built-in) with self-contained prompts. When the `build` plugin is installed, prefer its specialized delegates: `test-engineer` (tdd-red mode) for step 2 and `implementer` for steps 4 and 6 — the same templates apply. The main agent is the project manager; the worker is the engineer. This separation keeps the main context clean and uses the worker for what it's best at: focused, scope-bound code work.

Before planning tests, load `../coding-standards/SKILL.md` plus `../coding-standards/TESTING_AND_VERIFICATION.md`. Also load `../coding-standards/DESIGNING_MODULES.md` when modules, seams, or interfaces change, `../coding-standards/ASYNC_AND_WORKFLOWS.md` when the change touches retries, cancellation, concurrency, or detached work, `../coding-standards/TYPE_CONTRACTS.md` when seams or exported contracts change, and `../coding-standards/OBSERVABILITY.md` when safe summaries or telemetry are part of the behavior. This skill owns RED, GREEN, and REFACTOR sequencing; the standards topics own the detailed bar.

## When to Activate

- Writing new features or functionality.
- Fixing bugs (write the regression test that reproduces the bug FIRST).
- Refactoring code that has incomplete coverage (add characterization tests first, then refactor).
- Adding API endpoints or new public surface.
- Implementing a unit from a `spec` decomposition that involves new or changed behavior.

## When NOT to Activate

- Pure docs or config changes (no behavior to test).
- Pure formatter/codemod runs.
- Renames, import reorganization, or other mechanical refactors that don't change behavior AND already have full coverage on the affected areas. Verify coverage first; if unknown, treat as if it needs TDD.
- Spike / throwaway exploration. Note: most "throwaway" code survives. Be honest about scope before declaring TDD-exempt.

## Core Principles

### 1. Tests BEFORE Code
Always write the test first. The test fails (RED), then the smallest implementation makes it pass (GREEN), then optionally refactor (REFACTOR).

### 2. Coverage Requirements
- **Minimum 80% line + branch coverage** for the changed code.
- All edge cases covered (empty input, max input, null/undefined, error path).
- Boundary conditions verified (off-by-one, first/last element, threshold values).
- Error scenarios tested explicitly with the actual error type/message.

### 3. Test Pyramid

| Test type | Scope | Speed target | Tools (typical) |
|---|---|---|---|
| **Unit** | Single function / pure logic / utility | < 10ms each | jest, vitest, pytest, go test, cargo test |
| **Integration** | API endpoints, DB ops, service interactions | < 500ms each | supertest, pytest with httpx, go test with httptest |
| **E2E** | Full user flow through real surface | seconds each | playwright, cypress, selenium |

Aim for **many unit, fewer integration, fewest E2E**. E2E covers critical paths and irreversible flows; unit tests cover everything that can be unit-tested.

## Procedure

The loop has 7 steps. Repeat steps 2 through 5 as vertical slices: one behavior test or tightly related behavior cluster goes RED, then the smallest implementation goes GREEN, then the next slice starts. Do not write every test for the whole feature before any implementation unless the whole feature is genuinely one behavior. Steps 2, 4, and 6 (writing tests, writing implementation, refactoring) **should be delegated to a `worker`** with the prompts described below. Steps 1, 3, 5, and 7 (planning, commits, verification) are inline.

### Step 1 — Write the user journey or behavior statement (inline)

State what behavior you're adding in user-facing or contract-facing terms.

For user-facing code:
```
As a <role>, I want to <action>, so that <benefit>.
```

For non-user-facing code:
```
Given <preconditions>, when <event>, then <observable outcome>.
```

Examples:
- "As a user, I want to search markets semantically, so that I can find relevant markets without exact keywords."
- "Given a request with an expired session token, when the auth middleware runs, then it returns 401 with body `{ error: 'session_expired' }`."

Write this down — it anchors the tests in Step 2.

### Step 2 — Write failing test cases (delegate to `worker`)

Goal: produce the next failing test slice that covers one observable behavior or one tightly related cluster. The test should be reviewable as a behavior specification on its own.

**Delegation template** — pass this to a fresh `worker` invocation:

```
Goal: Write failing tests for the behavior below. Do NOT write the implementation.

Behavior:
<the user journey / Given-When-Then from Step 1>

Acceptance criteria from the spec:
- <criterion 1>
- <criterion 2>

Existing file structure (relevant):
- Test framework: <jest/vitest/pytest/go test/etc.>
- Test file location: <e.g., src/lib/rate-limit.test.ts>
- Source file (to be created/modified): <e.g., src/lib/rate-limit.ts>
- Repo conventions: <e.g., uses describe/it; mocks via vi.mock; coverage via vitest --coverage>

Requirements:
- Cover the next behavior slice, including its happy path, edge cases, boundary conditions, and error paths.
- Do NOT write tests for later slices yet. Return a short list of later slices to cover after this one goes GREEN.
- Each test asserts on observable behavior (return value, thrown error, side effect), not internal call sequences.
- Tests must be runnable individually (no order dependencies).
- DO NOT write the implementation. Stub the function/module with a placeholder that throws "not implemented" if needed.
- After writing, run the test command and confirm the new tests FAIL with the expected assertion errors (not syntax errors, not "module not found").

Deliverables:
- The test file content.
- Confirmation that running the suite shows N new failing tests for this slice, with the exact failure messages.
- The next 1-3 behavior slices to run after this one is GREEN.
- A list of any edge cases you considered but decided to skip, with reason.
```

Run the suite yourself after the worker returns and **confirm the tests fail for the right reason** (assertion failure, not a syntax error or unrelated crash). If a test passes immediately, the worker wrote a tautology — push back and require a real assertion.

### Step 3 — RED checkpoint commit (inline)

Once the failing tests are confirmed RED, commit them with an explicit RED label.

```
git add <test-file>
git commit -m "test(<scope>): add failing tests for <behavior>

RED: <N> tests failing as expected
- <one-line summary of test 1>
- <one-line summary of test 2>
- ..."
```

If running this skill in the context of a `spec` decomposition, you can let `commit-message-writer` draft the message and just paste it. The label `RED: <N> failing` should be present in the body so the GREEN commit can reference it.

### Step 4 — Implement the minimum to make tests pass (delegate to `worker`)

Goal: turn RED → GREEN with the simplest implementation possible. Resist generalization, abstractions, or "while I'm here" cleanup.

**Delegation template** — pass this to a fresh `worker` invocation:

```
Goal: Implement the minimum code needed to make these failing tests pass. Do NOT modify the tests.

Failing tests:
<paste the test file>

Test command:
<e.g., pnpm test src/lib/rate-limit.test.ts>

Current failure output:
<paste the failure output from the suite>

Existing code structure (relevant):
- Source file to create/modify: <path>
- Imports / dependencies available: <list>
- Existing patterns/conventions in this codebase: <e.g., uses async/await, error handling pattern, naming convention>

Requirements:
- Make ALL the failing tests pass.
- Do NOT modify the tests.
- Do NOT add functionality the tests don't require (no speculative generality, no extra error handling for cases not asserted).
- Run the suite after your implementation and confirm all new tests are GREEN AND no existing tests regressed.

Deliverables:
- The implementation file content.
- Confirmation that the full test suite is GREEN.
- Note any places where you were tempted to over-engineer but resisted.
```

After the worker returns, **run the full suite yourself** to verify:
- All new tests are GREEN.
- No existing tests regressed.
- The implementation is genuinely minimal (no speculative methods, parameters, or abstractions).

If regressions appeared, decide: is the regression a real bug exposed by the new code (fix it), or did the worker over-modify existing files (push back)?

### Step 5 — GREEN checkpoint commit (inline)

```
git add <source-file>
git commit -m "feat(<scope>): minimal implementation for <behavior>

GREEN: <N> tests passing, no regressions
- <one-line summary of what was implemented>"
```

### Step 6 — Refactor (optionally delegate to `worker`)

Goal: improve clarity, structure, and code smells now that you have a safety net.

**When to skip:** if the GREEN implementation is already clean and idiomatic, skip refactor entirely. Refactor is for actual smells, not for hypothetical improvements.

**Refactor signals:**
- duplication (extract function / module)
- long functions > 50 lines (split by step)
- unclear names (rename)
- mixed concerns in one function (separate)
- magic numbers (named constants)
- deeply nested conditionals (early-return guard clauses)

**Delegation template** — pass this to a fresh `worker` invocation:

```
Goal: Refactor the following code for clarity. Tests must remain GREEN throughout.

Current code:
<paste the source file>

Tests that must keep passing:
<paste or reference the test file>

Test command:
<e.g., pnpm test src/lib/rate-limit.test.ts>

Smells to address:
- <specific smell 1, with line reference>
- <specific smell 2>

Constraints:
- Behavior cannot change. Run the suite after each change; if it goes RED, revert that change.
- No new abstractions unless the refactor explicitly requires it.
- Apply the project's coding-standards (KISS, DRY only when same-reason-to-change, immutability defaults, descriptive naming).

Deliverables:
- The refactored file content.
- Confirmation tests are still GREEN.
- List of changes made and which smell each addressed.
```

**Verify the suite stays green** after the worker returns. If any test went RED during the refactor, the refactor changed behavior — revert and try again.

### Step 7 — REFACTOR checkpoint commit (optional, inline)

```
git add <source-file>
git commit -m "refactor(<scope>): <what changed>

GREEN: all tests still passing
- <smell 1 addressed>
- <smell 2 addressed>"
```

## After the Loop

Once GREEN and clean, the unit is **implementation-complete**, not **ship-ready**. Hand off:

1. **Run `verification-loop`** (skill, inline): build / type-check / lint / full suite with coverage. Address any gaps.
2. **Delegate to `change-review`** (droid): strict pre-merge correctness review of the diff. Catches what tests miss.
3. **Delegate to `security`** (droid) in parallel with change-review if the change touches auth, secrets, consent, untrusted input, or sensitive data.
4. **Delegate to `pr-describer`** (droid): synthesize the PR body from the same diff.
5. **Delegate to `commit-message-writer`** (droid) if the final squash-commit message needs polish.

## Git Checkpoint Rules

- Each checkpoint commit lives on the current branch and the active task line.
- Do not treat earlier unrelated commits as substitutes for the RED/GREEN commits of the current task.
- The compact-form workflow is acceptable: 1 commit for RED, 1 commit for GREEN, 1 optional commit for REFACTOR. You don't need a separate evidence-only commit if RED/GREEN labels in the message are clear.
- Verify each checkpoint is reachable from `HEAD` on the active branch before relying on it as evidence.
- The RED commit is the only proof that the tests fail without the implementation. Don't squash it before the GREEN commit lands.

## Delegation Map (per step)

| Step | Delegate to | Why |
|---|---|---|
| 1. Write user journey | `<self>` | Short, inline, agent-driven |
| 2. Write failing tests | `test-engineer` (tdd-red mode), else `worker` | Pins behavior; fails for the right reason by contract |
| 3. RED commit | `<self>` | Mechanical, agent runs git |
| 4. Implement | `implementer`, else `worker` | Minimal-diff discipline; fresh context avoids over-engineering |
| 5. GREEN commit | `<self>` | Mechanical |
| 6. Refactor (if needed) | `implementer`, else `worker` | Scope-bound code work with explicit smell list |
| 7. REFACTOR commit | `<self>` | Mechanical |
| After loop: verification | `<self>` guided by `verification-loop` skill | Mechanical command runs |
| After loop: code review | `change-review` (droid) | Specialized model for review |
| After loop: security review | `security` (droid) | Specialized for security |
| After loop: PR body | `pr-describer` (droid) | Synthesis specialist |
| After loop: commit message | `commit-message-writer` (droid) | Format-mechanical |

## Anti-Patterns

- **Writing implementation first, then tests** ("I'll write tests when I have time"). The after-the-fact test almost always tests the implementation, not the behavior.
- **Tests that don't fail before implementation lands.** A test that passes immediately is testing nothing — it's a tautology or it's testing existing unrelated code.
- **Asserting on implementation details.** Tests should assert on observable behavior (outputs, side effects, state changes), not internal call sequences (unless the call IS the contract, e.g., "audit-log function was called once with these args").
- **Skipping the RED state.** No. Run the suite. Watch it fail. Then implement.
- **Mocking everything.** Heavy mocks → tests assert that the mocks were called, not that the system works. Prefer real units; mock only at I/O boundaries.
- **Coverage as the goal.** Coverage is a floor, not a ceiling. 100% coverage with weak assertions is worse than 70% with strong ones.
- **One test file per source file as a rule.** Group tests by behavior, not file structure. Two related modules may share one test file; one complex module may need three.
- **Worker writes both tests and implementation in one shot.** Defeats the RED-GREEN discipline. Two separate worker invocations, with the RED commit in between.
- **Worker over-engineers in Step 4.** Push back if the implementation includes methods/parameters/abstractions the tests don't require. Minimal means minimal.
- **Refactoring without GREEN as the safety net.** Refactoring untested code is rewriting; risk goes up.

## Edge Cases

- **Bug fix where you discovered an existing failing test:** RED is already established. Commit the test on your branch first to anchor the regression to this work, then proceed to GREEN with the fix.
- **Behavior change (not addition):** modify the existing test to match the new expectation FIRST, watch it fail (RED), then change the implementation (GREEN). Don't change implementation and test in the same step.
- **Refactor with full coverage already:** no RED/GREEN cycle needed. The "test" is "the existing suite stays GREEN". Run before, run after, commit if green. Delegate to worker per Step 6 if the refactor is non-trivial.
- **Code that's hard to test directly** (filesystem, network, time, randomness): introduce a seam (interface / dependency injection) FIRST as its own TDD cycle, then test the dependent code. The seam itself can be one unit in a `spec` decomposition.
- **Legacy code with zero coverage:** write **characterization tests** first (capture current behavior, even if some of it is "buggy") to lock in a baseline, then refactor under the safety net, then add new behavior tests for changes.
- **Performance optimization:** the test asserts on **correctness**; a separate **benchmark** asserts on performance. Both should exist; only the test runs in CI on every commit. The benchmark runs in a separate pipeline or on-demand.
- **Test fixture is enormous / requires extensive setup:** factor out a builder/factory pattern as a side task BEFORE writing the test. Otherwise the test file becomes unreadable.
- **Two tests both fail GREEN but with different fixes:** the implementation is probably mixing concerns. Split the implementation, not the tests.

## Self-Check (before returning)

1. Did I delegate Steps 2, 4, and (if applicable) 6 to a fresh `worker` rather than write inline?
2. Did I verify the RED state by running the suite myself, not just trusting the worker?
3. Did I verify GREEN by running the suite myself, including no regressions?
4. Did I confirm the implementation is minimal (no speculative methods/parameters/abstractions)?
5. Are the RED/GREEN/REFACTOR commits all labeled in their messages?
6. Did I recommend the after-loop chain (`verification-loop` → `change-review` + `security` → `pr-describer` → `commit-message-writer`)?

If any answer is no, complete it before declaring the unit done.
