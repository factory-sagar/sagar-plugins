# sagar-plugins

A modular [Factory](https://factory.ai) plugin marketplace for taking engineering work from
an idea to a reviewed, merge-ready change.

The operator-facing workflow has four entry points:

```text
spec → implement → review-pr → ship
```

Behind them are specialist droids for investigation, planning, implementation, testing,
review, security, prompt work, and release prose. Deterministic hooks enforce safe pushes
and complete delivery.

**At a glance:** 7 plugins, 11 droids, 12 skills, 4 public workflows, and 1 guarded
idea-to-merge path.

## Quick start

Add the marketplace:

```bash
droid plugin marketplace add https://github.com/factory-sagar/sagar-plugins
```

Install the complete toolkit:

```bash
droid plugin install investigation@sagar-plugins
droid plugin install review@sagar-plugins
droid plugin install synthesis@sagar-plugins
droid plugin install meta@sagar-plugins
droid plugin install practices@sagar-plugins
droid plugin install build@sagar-plugins
droid plugin install guardrails@sagar-plugins
```

You can also browse and install individual plugins with `/plugins`.

Install individual plugins when you only need their droids or a standalone workflow. The
complete public workflows call across plugin boundaries:

| Workflow | Required plugins | Useful companions |
| --- | --- | --- |
| `spec` | `practices` | `investigation` for deeper repository or external research |
| `implement` | `build`, `practices` | `review` for the post-verification gate |
| `review-pr` | `review` | `build` for fixes, `practices` for design review, `investigation` for failure debugging |
| `ship` | `build`, `synthesis`, `review` | `investigation` for non-obvious CI failures |

## Core engineering flow
`spec → implement → review-pr → ship`
See [`docs/WORKFLOW.md`](./docs/WORKFLOW.md) for the canonical routing contract.

## Models

Each droid pins a model and reasoning effort suited to its job.

| Model | Role | Used by |
| --- | --- | --- |
| `gpt-5.6-sol` (xhigh) | Planning, repository investigation, and root cause | `planner`, `deep-understanding`, `debugger` |
| `gpt-5.6-terra` (high) | Implementation, testing, and precise config edits | `implementer`, `test-engineer`, `doc-generator` |
| `glm-5.2` (high) | Format-mechanical commit prose | `commit-message-writer` |
| `claude-opus-4-8` (xhigh/high) | Security, external research, and PR prose | `security`, `deep-research`, `pr-describer` |
| `kimi-k3` (max) | Correctness review of scoped diffs | `change-review` |


## Repository layout

```text
sagar-plugins/
├── .factory-plugin/
│   └── marketplace.json      # marketplace catalog
├── docs/
│   └── WORKFLOW.md           # detailed workflow contract
└── plugins/
    ├── investigation/        # 3 research and debugging droids
    ├── practices/            # planning droid + 8 policy skills
    ├── build/                # 2 execution droids + implement/ship
    ├── review/               # 2 review droids + review-pr
    ├── synthesis/            # commit and PR prose droids
    ├── meta/                 # prompt config editor + audit/apply loop
    └── guardrails/           # deterministic workflow hooks
```
