# synthesis

> Read-only droids that turn a diff into prose: PR descriptions and commit messages.

Two droids that take a diff and produce structured prose. One writes Conventional Commits messages, the other writes PR descriptions. Both are read-only: they output text for you to copy.

## Install

```bash
droid plugin install synthesis@sagar-plugins
```

## Droids

| Droid | When to delegate | Model | Reasoning | Tools |
| --- | --- | --- | --- | --- |
| `pr-describer` | Write a PR title and body from a diff. Structured what, why, testing, breaking changes, follow-ups, and notes for reviewers. | `claude-opus-4-8` | `high` | read-only + `Execute` |
| `commit-message-writer` | Write a Conventional Commits message from staged or specified changes. | `gpt-5.6-luna` | `medium` | read-only + `Execute` |

## Usage

- About to commit staged changes → `commit-message-writer`.
- About to open a PR → `pr-describer`.

## Models

`commit-message-writer` uses `gpt-5.6-luna` for low-cost mechanical output.
`pr-describer` uses `claude-opus-4-8` for template-aware prose synthesis.

## Related plugins

- **[`review`](../review/)**: hand review ownership to `review-pr` before invoking `pr-describer`; the PR body notes any reviewer hand-offs.
- **[`investigation`](../investigation/)**: `pr-describer` flags architectural questions for `deep-understanding`.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.
