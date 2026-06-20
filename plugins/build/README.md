# build

> Tools that change code: apply approved changes, write the missing tests, and resolve PR review comments.

Most of the marketplace investigates, reviews, and synthesizes. The build plugin applies: `implementer` turns approved findings and spec units into minimal diffs, `test-engineer` turns coverage gaps into tests, and the `resolve-pr-comments` skill fetches, applies, verifies, and pushes fixes for PR review comments.

## Install

```bash
droid plugin install build@sagar-plugins
```

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `implementer` | Apply an approved change set: `change-review` / `security` findings, a `spec` unit, or an explicit fix list. Makes the smallest change that closes each item, with targeted verification. | `gpt-5.4` | `high` | full read/write + `Execute` (verification only) |
| `test-engineer` | Find the riskiest untested behavior (gap analysis) or write the missing tests (write mode, including TDD RED). Pins current behavior; never encodes guesses. | `gpt-5.4` | `high` | full read/write + `Execute` (test runs only) |

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `resolve-pr-comments` | "fix droid comments", "resolve PR comments", "address review feedback", or a PR URL with intent to address comments | Fetches all review comments (bot and human), applies a fix for each actionable one (including `suggestion` blocks and prose feedback), verifies, and pushes. |

Command: `/resolve-pr-comments <PR URL or number>` runs the skill directly.

## Usage

1. `change-review` / `security` return findings → `implementer` applies them → re-review the delta.
2. `spec` decomposes a feature → `implementer` implements a unit → `test-engineer` covers it (or `tdd-workflow` orchestrates RED first).
3. `test-engineer` gap analysis ranks untested risk → parent picks gaps → `test-engineer` write mode fills them.
4. Review comments on a PR → `resolve-pr-comments` (or `/resolve-pr-comments <PR>`) applies, verifies, and pushes the fixes.
5. Root cause unknown? `debugger` (investigation plugin) diagnoses first, then `implementer` fixes.

## Models

The two droids run `gpt-5.4` at `high`, the marketplace's implementation tier: strong enough to reason about invariants and repo conventions without paying the `xhigh` audit premium on every edit. Deep reasoning stays where it belongs, in `debugger`, `deep-understanding`, and the reviewers. The `resolve-pr-comments` skill runs inline on your session model.

## Related plugins

- **[`review`](../review/)**: `change-review` and `security` produce the findings `implementer` consumes and the comments `resolve-pr-comments` resolves; both re-review its output.
- **[`investigation`](../investigation/)**: `debugger` hands `implementer` a fix plan and `test-engineer` a pin-it test; `deep-understanding` owns architectural questions too big for a minimal edit.
- **[`practices`](../practices/)**: `tdd-workflow` orchestrates `test-engineer` (RED) and `implementer` (GREEN); `verification-loop` gates the result.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.
