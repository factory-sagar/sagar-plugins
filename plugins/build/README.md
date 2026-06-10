# build

Two droids that change code on purpose. The rest of the marketplace investigates, reviews, and synthesizes — these two apply. `implementer` turns approved findings and spec units into minimal diffs; `test-engineer` turns coverage gaps into tests.

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `implementer` | Apply an approved change set: `change-review` / `security` findings, a `spec` unit, or an explicit fix list. Smallest change that closes each item, with targeted verification. | `gpt-5.4` | `high` | full read/write + `Execute` (verification only) |
| `test-engineer` | Find the riskiest untested behavior (gap analysis) or write the missing tests (write mode, including TDD RED). Pins current behavior; never encodes guesses. | `gpt-5.4` | `high` | full read/write + `Execute` (test runs only) |

## Typical flow

1. `change-review` / `security` return findings → `implementer` applies them → re-review the delta.
2. `spec` decomposes a feature → `implementer` implements a unit → `test-engineer` covers it (or `tdd-workflow` orchestrates RED first).
3. `test-engineer` gap analysis ranks untested risk → parent picks gaps → `test-engineer` write mode fills them.
4. Root cause unknown? `debugger` (investigation plugin) diagnoses first; `implementer` fixes after.

## Why these models

Both run `gpt-5.4` at `high` — the marketplace's implementation tier: strong enough to reason about invariants and repo conventions, without paying the `xhigh` audit premium on every edit. Deep reasoning stays where it belongs: `debugger`, `deep-understanding`, and the reviewers.

## Companion plugins (recommended)

- **[`review`](../review/)** — `change-review` and `security` produce the findings `implementer` consumes; both re-review its output.
- **[`investigation`](../investigation/)** — `debugger` hands `implementer` a fix plan and `test-engineer` a pin-it test; `deep-understanding` owns architectural questions that are too big for a minimal edit.
- **[`practices`](../practices/)** — `tdd-workflow` orchestrates `test-engineer` (RED) and `implementer` (GREEN); `verification-loop` gates the result.

Cross-plugin hand-offs are just naming suggestions; if you haven't installed the companion plugin the hand-off is a no-op recommendation, not an error.
