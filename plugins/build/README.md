# build

> Tools that change code: apply approved changes, write the missing tests, and fix PRs end-to-end.

Most of the marketplace investigates, reviews, and synthesizes. The build plugin applies: `implementer` turns approved findings and spec units into minimal diffs, `test-engineer` turns coverage gaps into tests, and the `fix-pr` skill fetches review comments, reasons about each one, fixes the valid bugs, replies and resolves threads, waits for CI, and approves the PR.

## Install

```bash
droid plugin install build@sagar-plugins
```

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `implementer` | Apply an approved change set: `change-review` / `security` findings, a `spec` unit, or an explicit fix list. Makes the smallest change that closes each item, with targeted verification. | `gpt-5.5` | `xhigh` | full read/write + `Execute` (verification only) |
| `test-engineer` | Find the riskiest untested behavior (gap analysis) or write the missing tests (write mode, including TDD RED). Pins current behavior; never encodes guesses. | `gpt-5.4` | `high` | full read/write + `Execute` (test runs only) |

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `fix-pr` | "fix this PR", "fix droid comments", "resolve PR comments", "address review feedback", or a PR URL with intent to address comments | Fetches all review comments (bot and human), reasons about whether each is a real bug, fixes the valid ones, replies to every comment, resolves threads, waits for CI, and approves the PR (or says "done" if it is your own). |

Command: `/fix-pr <PR URL or number>` runs the skill directly.

## Usage

1. `change-review` / `security` return findings → `implementer` applies them → re-review the delta.
2. `spec` decomposes a feature → `implementer` implements a unit → `test-engineer` covers it (or `tdd-workflow` orchestrates RED first).
3. `test-engineer` gap analysis ranks untested risk → parent picks gaps → `test-engineer` write mode fills them.
4. Review comments on a PR → `fix-pr` (or `/fix-pr <PR>`) triages, fixes, replies, resolves, waits for CI, and approves.
5. Root cause unknown? `debugger` (investigation plugin) diagnoses first, then `implementer` fixes.

## Models

`implementer` runs `gpt-5.5` at `xhigh` for high-stakes code changes where invariants and repo conventions matter. `test-engineer` stays on `gpt-5.4` at `high` for focused test gap analysis and test writing. The `fix-pr` skill runs inline on your session model.

## Related plugins

- **[`review`](../review/)**: `change-review` and `security` produce the findings `implementer` consumes and the comments `fix-pr` resolves; both re-review its output.
- **[`investigation`](../investigation/)**: `debugger` hands `implementer` a fix plan and `test-engineer` a pin-it test; `deep-understanding` owns architectural questions too big for a minimal edit.
- **[`practices`](../practices/)**: `tdd-workflow` orchestrates `test-engineer` (RED) and `implementer` (GREEN); `verification-loop` gates the result.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.
