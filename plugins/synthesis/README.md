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
| `pr-describer` | Write a PR title and body from a diff. Structured what, why, testing, breaking changes, follow-ups, and notes for reviewers. | `inherit` (Claude) | `high` | read-only + `Execute` |
| `commit-message-writer` | Write a Conventional Commits message from staged or specified changes. Fast and format-mechanical. | `glm-5.2` | default | read-only + `Execute` |

## Usage

- About to commit staged changes → `commit-message-writer`.
- About to open a PR → `pr-describer`.

## Models

`commit-message-writer` runs on `glm-5.2` because the format is mechanical and the output is short, so fast and cheap is the right call. `pr-describer` runs on Claude (`inherit`) because the body is multi-paragraph prose, and Claude has consistently produced the cleanest natural prose in this marketplace's testing.

## Related plugins

- **[`review`](../review/)**: run `change-review` (and optionally `security`) on the diff before invoking `pr-describer`; the PR body notes any reviewer hand-offs.
- **[`investigation`](../investigation/)**: `pr-describer` flags architectural questions for `deep-understanding`.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.
