---
name: coding-standards
description: Language-agnostic baseline coding conventions for naming, readability, immutability, error handling, and code-quality review. Use when starting a project, reviewing code for quality, refactoring for consistency, or onboarding a contributor. Triggers on "coding standards", "code quality", "naming conventions", "code style", "code review checklist".
---

# Coding Standards

Baseline coding conventions that apply across languages and frameworks. This is the shared floor — language-specific patterns (typescript-specific, python-specific, etc.) live elsewhere and override these defaults when they conflict.

## When to Activate

- Starting a new project or module.
- Reviewing code for quality and maintainability.
- Refactoring existing code to follow consistent conventions.
- Setting up linting, formatting, or type-checking rules.
- Onboarding a new contributor to the project's conventions.
- Sanity-checking AI-generated code before committing.

## When NOT to Activate

- A language-specific pattern skill is more relevant (e.g. a typescript-only style guide).
- The change is purely mechanical (formatter run, codemod) — no convention judgment needed.
- The user wants framework-specific advice (React composition, Django patterns, Spring conventions).

## Core Principles

### 1. Readability First
Code is read more than it's written. Optimize for the next reader (often a future you with no context).
- Clear, descriptive identifiers (variables, functions, types, files).
- Self-documenting code beats clever code beats heavily-commented clever code.
- Consistent formatting (use a formatter; don't argue about whitespace).

### 2. KISS — Keep It Simple

The simplest solution that meets the acceptance criteria wins. Premature abstraction is more expensive than the duplication it tries to prevent.

### 3. DRY — Don't Repeat Yourself, but…

Extract common logic when **the duplication has the same reason to change**. Two pieces of code that look alike but evolve independently are not duplication; they're parallel.

### 4. YAGNI — You Aren't Gonna Need It

Don't build for hypothetical futures. Add complexity when you actually need it. The biggest source of dead code is "we might want this later".

### 5. Immutability by default

Prefer creating new values to mutating existing ones:
- Returns from functions are new objects, not mutated inputs.
- Caller's data is treated as read-only unless the API explicitly takes ownership.
- State updates go through a single channel (reducer, store, repository) instead of being scattered.

This is not a hard rule — performance-critical inner loops often need mutation. The rule is: **mutation is opt-in and visible**, not the default.

## Naming

Names carry the intent of the code. Bad names are technical debt.

| Kind | Pattern (typical) | Example | Anti-example |
|---|---|---|---|
| Variables | descriptive nouns | `totalRevenue`, `pendingItems` | `x`, `data`, `result` |
| Booleans | `is/has/should/can` prefix | `isAuthenticated`, `hasItems` | `flag`, `auth`, `check` |
| Functions | verb + noun | `fetchUserProfile`, `validateEmail` | `process`, `handle`, `do` |
| Classes / Types | nouns | `User`, `OrderRepository` | `Manager`, `Helper`, `Util` |
| Constants | `SCREAMING_SNAKE` (in most languages) | `MAX_RETRIES`, `DEFAULT_TIMEOUT_MS` | `max`, `value` |
| Files | match the dominant export | `user-profile.tsx`, `order_repository.py` | `index.ts`, `utils.py` |

A name describing **what** something does or is is better than one describing **where** it lives in the architecture.

## Function Design

- One function does one thing. The "thing" might be at a high level of abstraction, but the function should not braid two concerns.
- Functions ≤ ~50 lines. Above that, look for steps that want to be their own functions.
- Pure functions (same input → same output, no side effects) are easier to test and reason about. Push side effects to the edges.
- Boolean parameters often signal a missing function. `processOrder(order, isRefund)` is usually two functions: `processOrder(order)` and `refundOrder(order)`.

## Error Handling

- **Validate at boundaries.** Untrusted input (HTTP request body, file I/O, external API response) is parsed/validated **once** at entry, then passed as a typed value through the rest of the system. Schema-based validation (zod, pydantic, marshmallow, etc.) is the cleanest way.
- **Fail fast with clear messages.** Don't silently coerce; throw / return Err.
- **Never swallow errors silently.** `catch (e) { /* nothing */ }` is a bug magnet. At minimum log; usually re-throw or wrap.
- **User-facing messages don't leak internals.** Stack traces, file paths, secrets stay server-side. Users get a stable, friendly message.
- **Error boundaries are explicit.** A single `try/catch` in a 500-line function buries failure modes. Place catches close to the operation that can fail.

## File Organization

- Many small files beat few mega files. **200–400 lines is typical, 800 is the upper limit before you should split.**
- Organize by feature/domain, not by file type. `users/` (with model + view + controller + tests) over `models/` + `views/` + `controllers/`.
- High cohesion within a module, low coupling between modules. Test: if you change one feature, how many modules do you touch? Should be ≤ 3.

## Code Smell Checklist

When reviewing (your own code or an AI's):

- **Long parameter lists** (> 4 positional args) → introduce an options object or split the function.
- **Deep nesting** (> 3 levels) → early-return guard clauses.
- **Magic numbers** → named constants.
- **Hidden side effects** (`getUser` that also writes a log to the DB) → split or rename to expose the side effect.
- **Stale comments** → either update or delete; stale comments lie.
- **Dead code** → delete; git remembers.
- **TODO without owner/date** → either fix now or file an issue with a real link.
- **Mutating inputs** → return a new value or document the mutation in the API.

## After Standards

Once code passes this checklist:
- Run `verification-loop` for the build/lint/test/coverage gate.
- Hand the diff to `change-review` for the correctness pass.
- Hand to `security` if the change touches auth, secrets, consent, or untrusted input.

## Companion Skills

- `tdd-workflow` — coding-standards is the floor; TDD is the floor on the BEHAVIOR side.
- `verification-loop` — automated quality gate that catches what review misses.
- `agentic-engineering` — operating principles, including reviewing AI-generated code.
- `spec` — defines acceptance criteria; coding-standards defines the bar each unit must clear.

## Anti-Patterns

- **Style debates without a formatter.** The conversation should be "is the formatter set up?" not "tabs vs spaces".
- **Treating standards as pixel-perfect law.** Standards are heuristics; sometimes the right answer is "violate this here, with a comment".
- **Long deprecation comments instead of deletion.** Delete; git history is the deprecation comment.
- **One mega-utility file** (`utils.py`, `helpers.ts`). It will swallow everything. Use focused names.
- **DRY extraction across boundaries that should remain independent.** Two services with similar code that evolve independently should not share a library.
- **Blanket "no comments" or "lots of comments" rules.** Add a comment when the code can't reasonably explain itself; remove comments that just paraphrase the code.
