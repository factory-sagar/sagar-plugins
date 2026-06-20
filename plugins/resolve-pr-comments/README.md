# resolve-pr-comments

Fetch review comments on a pull request, apply fixes, verify, and push.

## Skill

### `resolve-pr-comments`

Auto-invoked when the user asks to "fix droid comments", "resolve PR comments", "address review feedback", or provides a PR URL and wants comments addressed. Handles all review comments (bot and human), including ```suggestion blocks, prose feedback, and severity tags.

## Command

### `/resolve-pr-comments <PR URL or number>`

User-invoked slash command to resolve all review comments on a PR.

## Install

```bash
droid plugin marketplace add https://github.com/factory-sagar/sagar-plugins
droid plugin install resolve-pr-comments@sagar-plugins
```
