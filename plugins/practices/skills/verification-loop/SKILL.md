---
name: verification-loop
description: Quality-gate verification across build, type-check, lint, and test phases with coverage thresholds. Use after completing a feature, before opening a PR, after refactoring, or when you want to ensure quality gates pass before merging. Triggers on "verify", "quality gates", "pre-merge checks", "is this ready", "check before commit".
---

# Verification Loop

A four-phase quality gate to run after any non-trivial change. Each phase has a hard pass/fail signal; do not skip a phase, and do not move on while a phase is failing.

## When to Activate

- After completing a feature or non-trivial change.
- Before opening a PR.
- After a refactor (suite must stay green).
- When the user asks "is this ready" or "did I break anything".
- As part of an `agentic-engineering` eval-first loop (the regression eval).

## When NOT to Activate

- Mid-debug, when partial failures are expected. Wait until the change is complete enough to evaluate.
- Pure docs / config changes that don't run through build or tests.
- The repo has no validation tooling at all (note that as a finding, recommend setting it up via `coding-standards`).

## Procedure

### Phase 1 — Build / Compile

The change must build. Compilation errors are the cheapest bugs to find — find them first.

| Ecosystem | Command (typical) |
|---|---|
| Node (npm/pnpm/yarn) | `pnpm build`, `npm run build`, `yarn build` |
| Python | `python -m build`, or framework-specific (`manage.py check` for Django) |
| Go | `go build ./...` |
| Rust | `cargo build` |
| Java (Maven/Gradle) | `mvn compile`, `./gradlew build` |
| C/C++ | `make`, `cmake --build` |

Read the actual scripts in `package.json` / `pyproject.toml` / etc. before assuming. **Don't run a command that doesn't exist.**

If the build fails, **STOP and fix before continuing**. A green type-check on a broken build is meaningless.

### Phase 2 — Type Check

For typed languages, run the type-checker explicitly. Don't trust the build to do it (some build systems skip strict type checks).

| Ecosystem | Command (typical) |
|---|---|
| TypeScript | `pnpm tsc --noEmit`, `pnpm typecheck` (if defined) |
| Python | `pyright`, `mypy --strict` |
| Go | implicit in `go build` (note this) |
| Rust | implicit in `cargo build` (note this) |
| Java | implicit in `javac` (note this) |

Report all type errors. Fix new ones introduced by this change before continuing. Pre-existing type errors get noted but don't block — flag them under "Pre-existing issues spotted" so the next person can prioritize.

### Phase 3 — Lint

Style and policy violations.

| Ecosystem | Command (typical) |
|---|---|
| JS/TS | `pnpm lint`, `eslint .`, `biome check .` |
| Python | `ruff check .`, `flake8`, `pylint` |
| Go | `golangci-lint run`, `go vet ./...` |
| Rust | `cargo clippy --all-targets` |

Auto-fix what's auto-fixable (`--fix`, `--apply`), then commit the autofixes separately so the human-meaningful diff stays clean.

### Phase 4 — Test Suite + Coverage

Run the full suite. Coverage threshold from the project's policy (or 80% as the default per `tdd-workflow`).

| Ecosystem | Command (typical) |
|---|---|
| JS/TS | `pnpm test --coverage`, `vitest run --coverage` |
| Python | `pytest --cov=. --cov-report=term-missing` |
| Go | `go test ./... -coverprofile=cover.out && go tool cover -func=cover.out` |
| Rust | `cargo test`, `cargo tarpaulin` |

Report:
- Total tests, passing, failing, skipped.
- Coverage % (line + branch if available).
- New tests added vs total — `tdd-workflow` says new behavior gets new tests; verify it.

Fail conditions for the gate:
- Any new test failure.
- Coverage drops on changed files.
- Skipped tests added without justification.

## After All Four Phases Pass

The change is **gate-ready**, not necessarily **merge-ready**. Hand off to:

1. `change-review` — strict pre-merge correctness review (the human or AI reviewer; tests can be green and the change still wrong).
2. `security` — if the change touches auth, secrets, consent, untrusted input, or dependencies.
3. `pr-describer` — synthesize the PR body from the diff.

Verification is necessary but not sufficient.

## Output Template

Use this format when reporting verification results:

```
## Verification Results

| Phase | Status | Notes |
|---|---|---|
| Build | ✓ pass / ✗ fail | <command run, output summary> |
| Type-check | ✓ pass / ✗ fail / n/a | <new errors / pre-existing> |
| Lint | ✓ pass / ✗ fail | <auto-fixed / manual fixes / outstanding> |
| Tests | ✓ pass / ✗ fail | <X passing / Y failing / Z skipped, coverage W%> |

## Coverage on Changed Files
- `<file>` — <coverage % before> → <coverage % after>
- ...

## Pre-existing issues spotted (not caused by this change)
- <type error / lint warning / failing test that was already broken>
- ...

## Recommendation
- <green-light / fix issue X first / partial green: ship with caveats Y>
```

## Companion Skills

- `tdd-workflow` — verification-loop is the gate after the TDD loop completes.
- `coding-standards` — code that passes verification can still violate standards; standards is the human review.
- `agentic-engineering` — verification-loop is the regression eval in the eval-first loop.
- `spec` — units in the decomposition each pass through their own verification cycle.

## Companion Droids

- `change-review` — the next gate after verification (human/AI review).
- `security` — parallel gate for security-sensitive changes.

## Anti-Patterns

- **Skipping a phase because "it should be fine".** Run it. The cheapest bug found is the cheapest fixed.
- **Running tests but not checking coverage.** A passing suite that doesn't cover the new code is a false negative.
- **Treating warnings as errors with no opt-out.** Pre-existing issues block forever. Use the "Pre-existing issues spotted" section to decouple new failures from old.
- **Auto-fixing lint and tests in the same commit.** The lint diff swamps the actual change. Auto-fix → commit → write change → commit.
- **Running flaky E2E tests in the verification gate.** They poison the signal. Tag flaky tests, run them in a separate suite, fix them as their own work item.
- **Hiding skipped tests.** Skipped tests should require justification (a TODO with an issue link).

## Edge Cases

- **No type-checker** (untyped JS, Ruby, etc.): mark Phase 2 as `n/a` and rely more heavily on Phase 4 (tests).
- **No build step** (interpreted scripts, single-file): mark Phase 1 as `n/a`.
- **No test suite at all**: this is itself a finding. Recommend establishing TDD via `tdd-workflow` and standing up the suite.
- **CI runs these already**: still run them locally before pushing. Catch the issue when it's cheap to fix, not after a 10-min CI cycle.
- **Build / type-check requires an environment** (database running, env vars set): note the prerequisites, run them, and don't pretend a skipped phase is a green phase.
- **Phase commands take >5 minutes**: scope the run to changed files / changed packages where the tooling supports it (`pnpm --filter`, `pytest <path>`, `go test ./changed/...`).
