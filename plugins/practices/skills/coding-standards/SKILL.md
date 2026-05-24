---
name: coding-standards
description: Language-agnostic baseline coding conventions covering naming, readability, immutability, function design, file organization, error handling, and a code-smell review checklist. Recommends delegating actual code review to change-review (general correctness) and security (security-shaped concerns), while this skill defines the bar each change must clear. Use when starting a project, reviewing code for quality, refactoring for consistency, sanity-checking AI-generated code, or onboarding a contributor. Auto-activates on "coding standards", "code quality", "naming conventions", "code style", "code review checklist", "is this code clean", "review this for quality", "follow conventions", "best practices for this code".
---

# Coding Standards

Baseline conventions that apply across languages and frameworks. This is the shared floor; language-specific or framework-specific patterns (TypeScript-only style, Django-only conventions, etc.) live elsewhere and override these defaults when they conflict with project-specific norms.

This skill defines the **bar** each piece of code must clear. **The actual review** of a diff against the bar is best delegated to `change-review` (general correctness) and `security` (security-shaped concerns). This skill is the rubric; those droids are the reviewers.

## When to Activate

- Starting a new project or new module.
- Reviewing code for quality and maintainability (yours or AI-generated).
- Refactoring existing code to follow consistent conventions.
- Setting up linting, formatting, or type-checking rules for a new repo.
- Onboarding a new contributor to project conventions.
- Sanity-checking AI-generated code before committing.

## When NOT to Activate

- A language-specific style guide is more relevant and present in the project (e.g., a `typescript-patterns` or `python-patterns` skill, or a project-level `.editorconfig`/`prettierrc`/`ruff.toml` that defines stricter rules — those win).
- The change is purely mechanical (formatter run, codemod, automated import sort) — no convention judgment needed.
- The user wants framework-specific guidance (React composition, Django ORM patterns, Spring DI). This skill is generalist; defer to framework-specific guidance.

## Core Principles

### 1. Readability First

Code is read **far more** than it's written. Optimize for the next reader, who often has no context — including a future you in 6 months.

- Clear, descriptive identifiers (variables, functions, types, files).
- Self-documenting code beats clever code beats heavily-commented clever code.
- Consistent formatting — use a formatter; don't argue about whitespace in PRs.
- Comments explain **why**, not **what**. The code shows what.

### 2. KISS — Keep It Simple, Stupid

The simplest solution that meets the acceptance criteria wins. Premature abstraction is more expensive than the duplication it tries to prevent.

- "Could this be simpler?" — ask before merging.
- A clever 3-line solution that takes 20 minutes to understand is worse than a boring 10-line one.

### 3. DRY — Don't Repeat Yourself, but…

Extract common logic when **the duplication has the same reason to change**. Two pieces of code that look alike but evolve independently are **not** duplication — they're parallel.

The test: would a bug fix to A also need to apply to B? If yes, they're true duplicates — extract. If no (they happen to look similar today but their requirements come from different sources), leave them apart.

### 4. YAGNI — You Aren't Gonna Need It

Don't build for hypothetical futures. Add complexity when you actually need it. The biggest source of dead code is "we might want this later". The second biggest is "let me add this hook just in case."

### 5. Immutability by Default

Prefer creating new values to mutating existing ones:
- Returns from functions are new objects, not mutated inputs.
- Caller's data is treated as read-only unless the API explicitly takes ownership.
- State updates go through a single channel (reducer, store, repository) instead of being scattered across the codebase.

This is not a hard rule — performance-critical inner loops often need mutation. The rule is: **mutation is opt-in and visible**, not the default.

## Naming

Names carry the intent of the code. Bad names are technical debt that compounds.

| Kind | Convention (typical) | Good | Bad |
|---|---|---|---|
| Variables | descriptive nouns | `totalRevenue`, `pendingItems`, `apiKeyHash` | `x`, `data`, `result`, `obj` |
| Booleans | `is/has/should/can/did/will` prefix | `isAuthenticated`, `hasItems`, `shouldRetry` | `flag`, `auth`, `check`, `active` |
| Functions | verb + noun | `fetchUserProfile`, `validateEmail`, `parseSemver` | `process`, `handle`, `do`, `manage` |
| Classes / Types | nouns | `User`, `OrderRepository`, `RateLimitDecision` | `Manager`, `Helper`, `Util`, `Processor` |
| Constants | `SCREAMING_SNAKE` (most langs) | `MAX_RETRIES`, `DEFAULT_TIMEOUT_MS` | `max`, `value`, `cfg` |
| Files | match the dominant export | `user-profile.tsx`, `order_repository.py`, `rate-limit.ts` | `index.ts`, `utils.py`, `helpers.js` |
| Test files | mirror source + `.test.` | `rate-limit.test.ts` | `tests.ts` |

A name describing **what** something does or is is better than one describing **where** it lives in the architecture. `UserService` tells you nothing; `UserRepository` (it does data access for users) is better; `findUserByEmail` (it's a specific operation) is best.

## Function Design

- **One function does one thing.** The "thing" may be at a high level of abstraction, but the function should not braid two unrelated concerns.
- **Functions ≤ ~50 lines.** Above that, look for steps that want to be their own functions. Hard ceiling: 80 lines.
- **Pure functions** (same input → same output, no side effects) are easier to test and reason about. Push side effects to the edges of the system.
- **Boolean parameters often signal a missing function.** `processOrder(order, isRefund)` is usually two functions: `processOrder(order)` and `refundOrder(order)`.
- **Return early on guard conditions** rather than wrapping the happy path in deep nesting.

## Error Handling

- **Validate at boundaries.** Untrusted input (HTTP request body, file I/O, external API response) is parsed and validated **once** at entry, then passed as a typed value through the rest of the system. Schema-based validation (zod, pydantic, marshmallow, etc.) is the cleanest way.
- **Fail fast with clear messages.** Don't silently coerce; throw an error or return an Err type.
- **Never swallow errors silently.** `catch (e) { /* nothing */ }` is a bug magnet. At minimum log; usually re-throw or wrap with additional context.
- **User-facing messages don't leak internals.** Stack traces, file paths, internal IDs stay server-side. Users get a stable, friendly message.
- **Error boundaries are explicit.** A single try/catch in a 500-line function buries failure modes. Place catches close to the operation that can fail, with specific error types.
- **Distinguish expected errors from unexpected errors.** Expected (validation failure, 404) are part of the contract; unexpected (database down, OOM) deserve different handling and observability.

## File Organization

- **Many small files beat few mega-files.** 200–400 lines is typical; 800 is the upper limit before you should split.
- **Organize by feature/domain, not by file type.** `users/` (with model + view + controller + tests) beats `models/` + `views/` + `controllers/` + `tests/`.
- **High cohesion within a module, low coupling between modules.** Test: if you change one feature, how many modules do you touch? Should be ≤ 3 in most cases.
- **One responsibility per file.** A file mixing `getUserById`, `parseCsvForUpload`, and `computeBilling` is three files waiting to happen.

## Code Smell Checklist (use this for review)

When reviewing code (your own or an AI's), look for:

| Smell | Signal | Fix |
|---|---|---|
| Long parameter lists | > 4 positional args | Introduce an options object or split the function |
| Deep nesting | > 3 levels of `if`/`for`/`try` | Early-return guard clauses, extract inner blocks |
| Magic numbers | `if (status === 7)` | Named constants with semantic meaning |
| Hidden side effects | `getUser` that also writes a log to the DB | Split or rename to expose the side effect |
| Stale comments | comment contradicts the code | Either update or delete; stale comments lie |
| Dead code | unreachable branches, unused imports/vars | Delete; git remembers |
| TODO without owner/date | `// TODO: fix this` | Either fix now or file an issue with a link |
| Mutating inputs | function modifies its arg | Return a new value, or document the mutation in the API |
| God function | one function > 80 lines doing many things | Split by responsibility |
| God module | one module doing many things | Split by feature/concern |
| Coupling via globals | shared mutable state across modules | Encapsulate in a service / DI container |
| Boolean blindness | `func(true, false, true)` at call site | Use enums or named parameters |
| Premature abstraction | interface with one implementation | Inline until you need the second implementation |
| Inconsistent naming | `getUser`, `fetchAccount`, `loadOrder` | Pick one verb per operation type, apply consistently |

## After the Standards Pass

Once code is written or modified, the standards review should happen, but **the actual review of the diff should be delegated**. This skill defines what to look for; the droids find it.

1. **Run `verification-loop`** (skill, inline): catches anything tooling can catch (lint, type errors, test failures).
2. **Delegate to `change-review`** (droid, in `review` plugin): strict correctness pass through the code-smell checklist above plus correctness/migration/rollback risks.
3. **Delegate to `security`** (droid, in `review` plugin): if the change touches auth, secrets, consent, untrusted input, or dependencies.
4. Resolve findings.
5. **Delegate to `pr-describer`** (droid, in `synthesis` plugin) for the PR body.

The standards review is one of the lenses `change-review` uses. Don't try to do it inline on a large diff — that's what the droid is for.

## Delegation Map

| Task | Delegate to | Reason |
|---|---|---|
| Apply standards rubric to a diff | `change-review` (droid) | Specialized model + procedure for diff review |
| Check security-shaped standards (input validation, secrets handling, auth boundaries) | `security` (droid) | Specialized for security lens |
| Refactor a function to apply standards (extract, rename, simplify) | `worker` (Factory built-in) with explicit smell list | Self-contained code work |
| Set up linter / formatter / type-checker for a new repo | `worker` with the chosen toolchain | One-time setup, mechanical |
| Decide which language-specific overrides apply | `<self>` or hand off to `deep-understanding` | Project-architecture decision |
| Establish the standards baseline for a new codebase | `<self>` (write the docs/configs); then `doc-generator` if updating an existing AGENTS.md | Foundational decision |

## Anti-Patterns

- **Style debates without a formatter.** The conversation should be "is the formatter set up?" not "tabs vs spaces". Adopt prettier/biome/ruff/gofmt and move on.
- **Treating standards as pixel-perfect law.** Standards are heuristics; sometimes the right answer is "violate this here, with a comment explaining why".
- **Long deprecation comments instead of deletion.** Delete; git history is the deprecation comment.
- **One mega-utility file** (`utils.py`, `helpers.ts`, `common.js`). It will swallow everything. Use focused, named modules.
- **DRY extraction across boundaries that should remain independent.** Two services with similar code that evolve independently should not share a library; the shared library becomes a coupling source.
- **Blanket "no comments" or "lots of comments" rules.** Add a comment when the code can't reasonably explain itself (a hidden constraint, a workaround for a specific bug, behavior that would surprise a reader). Remove comments that just paraphrase the code.
- **Reviewing a giant diff inline.** Delegate to `change-review` — that's what it's for. Inline review of > 100 lines burns context and misses patterns.
- **Applying standards retroactively in unrelated PRs.** "While I'm here, let me fix all the naming" balloons review and obscures the real change. Surface as a follow-up issue.
- **Lecturing the AI/contributor on standards instead of running the standards.** Set up the linter; let the tool tell them.

## Edge Cases

- **Generated code** (codegen output, schema-derived types, etc.): exempt from standards review beyond "does it compile and tests pass". The generator owns the style.
- **Vendored / third-party code in-tree**: exempt; standards apply to your code, not theirs. Mark the directory in lint config.
- **Performance-critical inner loop** that violates KISS or immutability for measurable reason: leave a comment with the benchmark result. Standards yield to evidence-based performance needs.
- **Test code**: looser standards on test files are acceptable (longer functions, more setup code, named test helpers). The bar is "the test is correct and readable", not "the test follows production conventions to the letter".
- **Migration code that's run once**: standards still apply to readability and correctness; less to long-term maintainability.
- **Single-developer prototype**: defer most standards until the code survives 2 weeks. Premature standards on throwaway code is wasted effort. Note: be honest about whether it's actually throwaway.
- **Code from an AI agent that violates standards**: don't fix it inline before review. Either ask the worker to redo with a constraint added ("rewrite using guard clauses, max nesting 2"), or surface it as a `change-review` finding for the human reviewer to decide.
- **Project explicitly opts out of a standard** (e.g., team prefers `class` over functional components in React): override this skill's defaults with the project decision. Document the override.

## Self-Check (before declaring code "passes standards")

1. Did I use a formatter to handle whitespace/style, not human judgment?
2. Are names descriptive (would a new reader understand the intent)?
3. Are functions doing one thing?
4. Are errors handled at boundaries, not swallowed?
5. Are files appropriately sized and organized by feature?
6. Did I delegate the actual diff review to `change-review` (and `security` if relevant) rather than try to review inline?
7. For violations of standards, did I either fix them or leave a justifying comment?

If any answer is no, address it before declaring the change ready for `change-review`.
