# guardrails

Enforcement layer for the sagar-plugins fleet. No droids, no skills, no MCP: three lifecycle hooks that turn the marketplace's advisory practices into mechanical policy.

## Hooks

### 1. Destructive-command policy (`PreToolUse` on `Execute`)

Runs before every shell command, independent of the session autonomy level.

| Decision | Commands |
| --- | --- |
| **deny** | `rm -rf` targeting `/` or `~`, `sudo rm -r`, force push to `main`/`master`, `mkfs`, `dd of=/dev/...`, fork bombs, recursive `chmod 777 /` |
| **ask** | `git reset --hard`, `git clean -f`, broad `git checkout .` / `git restore .`, any force push, `git stash drop/clear`, `git branch -D`, other `rm -rf`, `find -delete` |

Everything else falls through to the normal permission flow.

### 2. Verification gate (`Stop`)

Parses the session transcript when Droid tries to finish. If files were modified (directly via `Edit`/`Create`/`ApplyPatch`, or via `Task` delegation to `implementer` / `test-engineer`) and no verification command ran successfully after the last edit, the stop is blocked once with instructions to run the project's verification.

Design properties:

- **Single nudge.** When `stop_hook_active` is true the gate always allows, so it can never loop.
- **Research sessions pass.** No edits, no gate.
- **Docs-only edits pass.** Sessions touching only `.md`/`.mdx`/`.txt`/`.rst` files are exempt.
- **Self-resolving.** If the project has no verification commands, Droid states that and the next stop passes.

Verification evidence: an `Execute` call matching common test/lint/typecheck/build invocations (npm/pnpm/yarn/bun scripts, pytest, go test, cargo test/check, make test, tsc, eslint, ruff, gradle/mvn, etc.) that did not fail, or a `Task` delegation whose prompt clearly runs verification.

### 3. Fleet router (`SessionStart` on `startup|clear|compact`)

Injects [`fleet-cheatsheet.md`](./hooks/fleet-cheatsheet.md) (~400 tokens) into context so the main agent routes work to the fleet's droids and skills without being prompted. Re-injected after compaction so the routing map survives context compression.

## Escape hatches

| Mechanism | Effect |
| --- | --- |
| `GUARDRAILS_DISABLE=1` (env) | Disables all three hooks |
| `GUARDRAILS_STOP_GATE=off` (env) | Disables only the verification gate |
| `.factory/guardrails-off` (marker file in project root) | Disables the verification gate for that project |

## Limitations

- Hook scripts require `python3` and a POSIX shell (macOS/Linux; not Windows).
- The verification gate inspects the top-level transcript only; edits made by subagents other than `implementer`/`test-engineer` are not detected.
- Delegations to `implementer`/`test-engineer` count as edits, never as verification evidence, by design: the parent session must run (or delegate) verification after they return.
- The command policy is pattern-based and anchored to command position (quoted mentions like `echo "rm -rf /"` do not trigger); it narrows the blast radius but is not a sandbox.

## Install

```bash
droid plugin install guardrails@sagar-plugins
```
