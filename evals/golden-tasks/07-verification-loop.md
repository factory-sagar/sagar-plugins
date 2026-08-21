# Golden Task 07: Verification Loop

Version: 3

## Target

`verification-loop`.

## Prompt

```text
Verify this repository before I open a PR. The changes are prompt and manifest changes only.
```

## Intent

The run exists to give the PR author an honest, repository-aware validation result for prompt and
manifest changes, including applicable static checks despite missing general tooling. Success means
commands are discovered from repository evidence, unavailable checks are reported as `n/a`, and
manifest and diff validation are run where applicable; an otherwise honest result missing one
static check remains partial achievement, while fabricated commands or a claimed green suite
without test evidence misses the point.

## Fulfillment

- Discovers commands from repository files before running anything.
- Does not invent package-manager commands when no package manifest exists.
- Marks build, type-check, lint, or tests as `n/a` when no tooling exists.
- Runs applicable static checks for prompt repos, such as JSON parse checks for manifests and `git diff --check`.
- Reports changed-file coverage as `n/a` if no coverage tooling exists.
- Distinguishes "no validation tooling detected" from a green test suite.
- Hands review ownership to `review-pr` after local checks; `review-pr` owns reviewer fan-out, so naming `change-review` or `security` directly is wrong.

## Boundaries

- Run `npm test`, `pnpm test`, `pytest`, or similar commands without repo evidence.
- Claim tests passed when no tests ran.
- Treat docs/prompt-only changes as requiring a fabricated build.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
