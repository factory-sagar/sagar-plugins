# resolve-pr-comments

> Fetch PR review comments, apply fixes, verify, and push.

Fetch review comments on a pull request, apply the fixes, verify, and push. Available as an auto-loaded skill and a slash command.

## Install

```bash
droid plugin install resolve-pr-comments@sagar-plugins
```

## Skills

| Skill | Triggers on | What it does |
| --- | --- | --- |
| `resolve-pr-comments` | "fix droid comments", "resolve PR comments", "address review feedback", or a PR URL with intent to address comments | Handles all review comments (bot and human), including `suggestion` blocks, prose feedback, and severity tags. |

## Usage

- Auto: ask to "resolve PR comments" or "address review feedback" and the skill loads.
- Command: `/resolve-pr-comments <PR URL or number>` resolves all review comments on a PR.

## Related plugins

- **[`review`](../review/)**: `change-review` and `security` produce the kind of comments this plugin resolves.
- **[`build`](../build/)**: hand non-trivial fixes to `implementer` once the comments are triaged.

Cross-plugin hand-offs are naming suggestions. If you haven't installed the companion plugin, the hand-off is a no-op recommendation, not an error.
