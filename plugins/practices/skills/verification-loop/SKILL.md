---
name: verification-loop
version: 1.0.0
description: |
  Four-phase quality gate (build, type-check, lint, tests with coverage) with explicit worker
  delegation per phase for long-running commands. Catches regressions before review, surfaces
  pre-existing issues without blocking on them, and hands the gate-ready diff to `change-review`
  and `security`.
  Use when:
  - Completing a feature or non-trivial change
  - Preparing to open a PR
  - Finishing a refactor (suite must stay green; this confirms it)
  - Finishing a `tdd-workflow` loop (the natural next step)
  - User asks "is this ready", "did I break anything", "run the checks"
  - As the regression eval in an `agentic-engineering` eval-first loop
tags: [quality-gates, verification, testing, ci, build, lint, type-check]
---

# Verification Loop

A four-phase quality gate to run after any non-trivial change. Each phase has a hard pass/fail signal. Do not skip a phase. Do not move on while a phase is failing. Each phase that runs a potentially long command **should be delegated to a `worker`** (Factory built-in) so the main agent's context isn't filled with command output — the worker returns a summary, the main agent decides the next move.

Before running the loop, load `../coding-standards/SKILL.md` and `../coding-standards/TESTING_AND_VERIFICATION.md`. Also load `../coding-standards/TYPE_CONTRACTS.md` when exported contracts or type safety changed, `../coding-standards/ASYNC_AND_WORKFLOWS.md` when async ownership changed, and `../coding-standards/OBSERVABILITY.md` when verification must cover telemetry or safe error surfaces. This skill owns command discovery and gate sequencing; the standards topics own the detailed bar.

## When to Activate

- After completing a feature or non-trivial change.
- Before opening a PR.
- After a refactor (suite must stay green; this confirms it).
- After the `tdd-workflow` loop completes (this is the natural next step).
- When the user asks "is this ready", "did I break anything", "run the checks".
- As part of the regression eval in an `agentic-engineering` eval-first loop.

## When NOT to Activate

- Mid-debug, when partial failures are expected. Wait until the change is complete enough to evaluate.
- Trivial prose-only docs or asset changes with no prompt, manifest, config, generated artifact, or plugin-discovery impact.
- The repo has no validation tooling at all and no static file formats to validate. If manifests, config files, prompt files, markdown, YAML, JSON, or lockfiles changed, run the applicable static checks instead of stopping.

## Procedure

The procedure has four mandatory phases plus a routing decision. Each phase has a clear pass/fail signal. For each phase, you may either run inline (if the command is fast and you want the output in context) or **delegate to `worker`** (if the command is slow, noisy, or you want to keep main context clean).

### Phase 0 — Discover commands

Goal: figure out which commands this repo actually uses for each phase. **Don't assume** — repos lie about what their `npm test` actually runs.

Inline. Use these signals:
- `package.json` `scripts` section (Node ecosystems)
- `pyproject.toml` `[project.scripts]` and `[tool.*]` sections
- `Cargo.toml` workspace + tooling sections
- `go.mod` plus any `Makefile` or `mage.go`
- `Makefile`, `justfile`, `taskfile.yml` at root
- CI config (`.github/workflows/*.yml`, `.gitlab-ci.yml`) for the canonical command set
- README "Development" or "Contributing" section

If commands genuinely aren't declared, look for the framework defaults (`pnpm exec tsc --noEmit` for TypeScript, `ruff check .` for Python ruff, etc.) — and **note the inferred command** in the output so the user can confirm.

If you can't determine the command for a phase, mark that phase `n/a (no tooling detected)` in the output. Don't fabricate a command.

For prompt, plugin, config, and documentation repositories with no build/test tooling, still run applicable static checks based on changed files:

- JSON manifests or config: parse every changed JSON file.
- YAML frontmatter or config: validate frontmatter delimiters and parse YAML when a parser is available.
- Markdown/prompt diffs: run `git diff --check` and inspect changed links or relative paths that affect plugin discovery.
- Plugin marketplaces: verify root and per-plugin manifest counts/descriptions match the files on disk.

Report these under the closest applicable phase or a `Static checks` note. Do not call the repository green just because no tests exist.

### Phase 1 — Build / Compile

The change must build. Compilation errors are the cheapest bugs to find — find them first.

**Delegation template** for a long build — pass to `worker`:

```
Goal: Run the build command and report whether it succeeded. If it failed, summarize the first 5 errors with file:line and error message. Do NOT fix anything.

Command: <e.g., pnpm build>
Working directory: <repo root>

Constraints:
- Read-only. Do not modify any files.
- Capture stdout+stderr; report only the summary.
- If the build exits non-zero, parse the output for the first 5 errors (file:line + message).
- If output is so long it would saturate context, return only the summary table + the first 5 errors, not the full log.

Deliverables:
- Exit code (0 / non-zero).
- Pass/fail verdict.
- If failed: first 5 errors with file:line and 1-line message each.
- Wall-clock duration.
```

Inline version (for fast builds < 30s): just run the command yourself and capture the result.

**Pass condition:** exit code 0, no warnings escalated to errors.
**Fail condition:** any non-zero exit code. **STOP** and fix before continuing. A green type-check on a broken build is meaningless.

### Phase 2 — Type Check

For typed languages, run the type-checker explicitly. Don't trust the build to do it (some build systems skip strict type checks).

| Ecosystem | Command (typical) |
|---|---|
| TypeScript | `pnpm tsc --noEmit`, `pnpm typecheck` (if defined) |
| Python | `pyright`, `mypy --strict` |
| Go | implicit in `go build`; explicit via `go vet ./...` |
| Rust | implicit in `cargo check` / `cargo build` |
| Java | implicit in `javac` / `mvn compile` |

**Delegation template** for slow type-checks:

```
Goal: Run the type-checker and report new vs pre-existing errors. Do NOT fix anything.

Command: <e.g., pnpm tsc --noEmit>
Working directory: <repo root>
Files changed in this branch vs main: <list>

Constraints:
- Read-only.
- Distinguish errors in changed files (new errors — block the merge) from errors elsewhere (pre-existing — flag but don't block).
- If output is enormous, summarize: total error count, errors in changed files, sample 3 of each.

Deliverables:
- Pass/fail (where pass = zero new errors in changed files).
- Table: error type | count in changed files | count elsewhere.
- Up to 5 new errors with file:line + message.
- Wall-clock duration.
```

**Pass condition:** zero new type errors in files changed by this branch.
**Fail condition:** any new type error introduced by the change. Fix it.
**Pre-existing type errors:** flag under "Pre-existing issues spotted" but don't block this gate.

### Phase 3 — Lint

Style and policy violations.

| Ecosystem | Command (typical) |
|---|---|
| JS/TS | `pnpm lint`, `eslint .`, `biome check .` |
| Python | `ruff check .`, `flake8`, `pylint` |
| Go | `golangci-lint run`, `go vet ./...` |
| Rust | `cargo clippy --all-targets -- -D warnings` |
| Java | `mvn checkstyle:check`, `./gradlew check` |

Auto-fix what's auto-fixable (`--fix`, `--apply`, etc.), then **commit the auto-fixes in a separate commit** so the human-meaningful diff stays clean. The auto-fix commit message should be `chore: apply auto-fixable lint`.

**Delegation template** for lint with potential auto-fix:

```
Goal: Run lint with auto-fix. Report what was auto-fixed and what remains. Do NOT commit anything — just report.

Command (check): <e.g., pnpm lint>
Command (auto-fix): <e.g., pnpm lint --fix>
Working directory: <repo root>

Constraints:
- After auto-fix, re-run check.
- If there are unfixed violations, report them grouped by rule.
- Do NOT make a commit — return the modified files and the remaining violation list; the main agent will decide whether to commit.

Deliverables:
- Files modified by auto-fix (list).
- Remaining violations table: rule | count | sample (1-2 examples with file:line).
- Whether the post-fix run is clean.
```

**Pass condition:** zero remaining violations after auto-fix.
**Fail condition:** unfixed violations. Decide per-rule: fix manually, suppress with a justification comment, or escalate as a code-standards discussion.

### Phase 4 — Test Suite + Coverage

Run the full suite. Coverage threshold from the project's policy (`tdd-workflow` defaults to 80%).

| Ecosystem | Command (typical) |
|---|---|
| JS/TS | `pnpm test --coverage`, `vitest run --coverage` |
| Python | `pytest --cov=. --cov-report=term-missing` |
| Go | `go test ./... -coverprofile=cover.out && go tool cover -func=cover.out` |
| Rust | `cargo test`, `cargo tarpaulin --skip-clean` |
| Java | `mvn test jacoco:report`, `./gradlew test jacocoTestReport` |

**Delegation template** for the test suite (almost always worth delegating — tests can be long and noisy):

```
Goal: Run the test suite with coverage. Report pass/fail, coverage on changed files, and any new failures. Do NOT fix anything.

Command: <e.g., pnpm test --coverage>
Working directory: <repo root>
Files changed in this branch vs main: <list>

Constraints:
- Read-only.
- Surface: total tests, passing, failing, skipped, coverage % (line + branch if available).
- For coverage, specifically report the coverage on changed files before vs after this branch.
- For failures, return the test name, file:line, and the first 10 lines of failure output (assertion message + stack trace head).
- Identify any tests that became flaky (skipped due to retry, intermittent fails).

Deliverables:
- Suite summary table.
- Coverage on changed files: before / after / delta.
- Up to 5 failing tests with name, file, and failure head.
- Skipped tests added in this branch (with reason if findable in the test code).
- Wall-clock duration.
```

**Pass conditions:**
- Zero new test failures.
- Coverage on changed files >= 80% (or project policy).
- Skipped tests added are justified (TODO with an issue link).

**Fail conditions:**
- Any new test failure (introduced or surfaced by this change).
- Coverage drops on changed files (a new untested line was added).
- Skipped tests added without justification.

## After All Four Phases Pass

The change is **gate-ready**, not necessarily **merge-ready**. The next moves are mandatory:

1. **Delegate to `change-review`** (droid in the `review` plugin) — strict pre-merge correctness review of the diff. Catches what tests miss: race conditions, rollback hazards, event reliability, consent gaps.
2. **Delegate to `security`** (droid in the `review` plugin) **in parallel with change-review** if the change touches:
   - Authentication / authorization paths
   - Secrets, tokens, API keys, env vars
   - Consent / privacy gates
   - Untrusted input handling
   - Dependency additions or version bumps (CVE check)
3. Resolve all findings from change-review and security.
4. **Delegate to `pr-describer`** (droid in the `synthesis` plugin) — synthesize the PR body from the diff, including findings/hand-offs from the review droids.
5. **Delegate to `commit-message-writer`** (droid in the `synthesis` plugin) for the final squash commit if needed.

Verification is necessary but not sufficient. Tests can be green and the change still wrong (untested behavior, design flaws). The reviewer droids are the next gate.

## Output Template

Use this exact format when reporting verification results:

```
## Verification Results

| Phase | Status | Notes |
|---|---|---|
| Build | ✓ pass / ✗ fail / n/a | <command run, duration, output summary> |
| Type-check | ✓ pass / ✗ fail / n/a | <new errors / pre-existing> |
| Lint | ✓ pass / ✗ fail / n/a | <auto-fixed / manual / outstanding> |
| Tests | ✓ pass / ✗ fail / n/a | <X passing / Y failing / Z skipped, coverage W%> |

## Coverage on Changed Files
| File | Before | After | Delta |
|---|---|---|---|
| `<path>` | <%> | <%> | <±%> |

## Failures (if any)
- **<test name>** — `<file:line>`
  - <failure message head, 2-3 lines max>

## Pre-existing issues spotted (not blocking this change)
- <type error / lint warning / failing test that was already broken>
- <...>

## Auto-fixes applied (separate commit recommended)
- <count> lint violations auto-fixed across <N> files.
- Suggested commit: `chore: apply auto-fixable lint`.

## Recommendation
- ✓ **Green-light:** all phases pass; hand off to `change-review` (+ `security` if applicable), then `pr-describer`.
- OR ⚠ **Fix first:** <specific phase> failed with <N> issues; address before proceeding.
- OR ⚠ **Partial green:** ship with caveats <X, Y> (only if user explicitly accepts).
```

## Delegation Map (per phase)

| Phase | Run inline? | Or delegate to `worker`? | Reason |
|---|---|---|---|
| 0. Discover commands | Inline always | — | Fast file reads (package.json, scripts) |
| 1. Build | Inline if < 30s | `worker` if longer | Build output can be huge; worker returns summary |
| 2. Type-check | Inline if < 30s | `worker` if longer or if errors are many | Same — output volume |
| 3. Lint | Inline | `worker` if doing auto-fix | Auto-fix touches files; worker isolates the change set |
| 4. Tests | **Almost always delegate to `worker`** | — | Tests are long and noisy; worker summarizes |
| After: code review | `change-review` (droid) | — | Specialized model |
| After: security review | `security` (droid) | — | Specialized model |
| After: PR body | `pr-describer` (droid) | — | Synthesis specialist |

## Anti-Patterns

- **Skipping a phase because "it should be fine."** Run it. The cheapest bug is the one you find before review.
- **Running tests but not checking coverage.** A passing suite that doesn't cover the new code is a false negative.
- **Treating warnings as errors with no opt-out.** Pre-existing issues block forever. Use the "Pre-existing issues spotted" section to decouple new failures from old.
- **Auto-fixing lint and writing real changes in the same commit.** The lint diff swamps the actual change. Auto-fix → commit → write change → commit.
- **Running flaky E2E tests in the verification gate.** They poison the signal. Tag flaky tests, run them in a separate suite, fix them as their own work item.
- **Hiding skipped tests.** Skipped tests should require justification (a TODO with an issue link).
- **Fabricating a command** because you can't find one declared. Mark the phase `n/a (no tooling detected)` and surface it as a finding.
- **Letting the worker run a phase and accepting its output without sanity-checking.** The worker's "pass" verdict still needs verification — at minimum cross-check the exit code matches.
- **Treating verification as the final gate.** It's the FIRST gate. Code review and security review come after. Don't skip them.
- **Running all four phases sequentially when the user only changed docs.** Match the gate to the change shape: docs-only diff doesn't need type-check or tests.

## Edge Cases

- **No type-checker** (untyped JS, Ruby, etc.): mark Phase 2 as `n/a` and rely more heavily on Phase 4 (tests).
- **No build step** (interpreted scripts, single-file): mark Phase 1 as `n/a`.
- **No test suite at all**: this is itself a finding. Output the gap, recommend establishing TDD via `tdd-workflow` and standing up the suite, and either stop or proceed with explicit "no test gate" caveat for this PR (user decides).
- **CI runs these already**: still run locally before pushing. Catch the issue when it's cheap to fix, not after a 10-min CI cycle. Use CI as a redundant gate, not the primary one.
- **Build / type-check requires an environment** (database running, env vars set): note prerequisites in the output, run them, and don't pretend a skipped phase is a green phase. If you can't set up the environment, mark the phase `blocked` with reason.
- **Phase commands take > 5 minutes total**: scope the run to changed files / changed packages where the tooling supports it (`pnpm --filter <pkg>`, `pytest <path>`, `go test ./changed/...`). Worker delegation is mandatory here — the main agent can't sit on a 5-min wait.
- **Output is too large for one worker response**: split the phase. Run build alone, return summary; run type-check alone, return summary; etc.
- **Test suite has known-flaky tests that randomly fail**: run twice; if both runs agree on a failure, treat as real; if one fails and one passes, treat as flaky and tag the test. Don't accept a single run as definitive for flaky tests.
- **The change is so small (single line, single typo) that running 4 phases is overkill**: skip Phase 1 + Phase 3 if appropriate; always run Phase 2 (cheap) and Phase 4 on the affected test file at minimum.
- **CI is in a broken state independent of this change**: note in Pre-existing issues; recommend a fix-CI work item; proceed with local verification only.

## Self-Check (before returning)

1. Did I discover the actual commands from manifests/CI/README, not assume?
2. Did I run (or delegate) ALL four phases that apply, none skipped silently?
3. Did I distinguish new failures (block) from pre-existing (flag)?
4. Did I report coverage specifically on the CHANGED files, not just overall?
5. Did I recommend the after-loop chain (`change-review` + `security` if applicable → `pr-describer`)?
6. Did I separate auto-fix changes from the user's real change in commit recommendations?
7. Did I surface any tooling gaps (no type-checker, no test suite, no CI) as findings?

If any answer is no, fix or document it before returning.
