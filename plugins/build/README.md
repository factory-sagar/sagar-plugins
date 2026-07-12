# build

> Tools that change code: apply approved changes, write the missing tests, and fix PRs end-to-end.

The build plugin applies and lands: `implementer` executes approved units, `test-engineer`
pins risky behavior, `implement` chooses the execution discipline, and `ship` owns commit,
push, PR freshness, CI, and thread closure. Review-comment handling lives in `review-pr`.

## Install

```bash
droid plugin install build@sagar-plugins
```

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `implementer` | Apply an approved change set with minimal edits and targeted verification. | `gpt-5.6-terra` | `high` | full read/write + verification |
| `test-engineer` | Rank untested risk or write behavior-pinning tests, including TDD RED. | `gpt-5.6-terra` | `high` | tests-only writes + execution |

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `implement` | "implement this", "apply this change set", "build this unit" | Routes an approved change set to `implementer`, new behavior without one to `tdd-workflow`, and small mechanical changes inline. Carries the Deviations contract in every path and finishes with `verification-loop`. |
| `ship` | "ship it", "push", "monitor ci", "clean up the PR", "merge it if CI passes" | Lands finished work: commit, push, update the template-conformant PR body, watch CI, and resolve review threads. It merges only when explicitly requested and all delivery gates pass. |

The public entry points are `/implement <task>` and `/ship`.

## Usage

1. `change-review` / `security` return findings → `implementer` applies them → re-review the delta.
2. `spec` decomposes a feature → `implementer` implements a unit → `test-engineer` covers it (or `tdd-workflow` orchestrates RED first).
3. `test-engineer` gap analysis ranks untested risk → parent picks gaps → `test-engineer` write mode fills them.
4. Review comments on a PR → `review-pr` comments mode.
5. Root cause unknown? `debugger` diagnoses first, then `implementer` fixes.

## Related plugins

- **[`review`](../review/)**: `review-pr`, `change-review`, and `security` produce the findings `implementer` consumes.
- **[`investigation`](../investigation/)**: `debugger` hands `implementer` a fix plan and `test-engineer` a pin-it test; `deep-understanding` owns architectural questions too big for a minimal edit.
- **[`practices`](../practices/)**: `tdd-workflow` orchestrates `test-engineer` (RED) and `implementer` (GREEN); `verification-loop` gates the result.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.
