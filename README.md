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

**At a glance:** 7 plugins, 14 droids, 13 skills, 4 public workflows, and 1 guarded
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

[`docs/WORKFLOW.md`](./docs/WORKFLOW.md) is the detailed workflow contract. The main path is:

```text
IDEA
  │
  ▼
/spec
  ├─ planner, the default path for evidence-backed decisions and executable units
  ├─ discovering-unknowns, before planning unfamiliar or taste-shaped work
  ├─ architecture-scan, first when the question is ownership or code placement
  ├─ grilling, when the current plan still has a major unresolved decision
  └─ tech-spec, when an approved plan needs typed contracts and call stacks
  │
  ▼ operator approves the plan
/implement <unit>
  ├─ approved change set → implementer
  ├─ new behavior → tdd-workflow → test-engineer (RED) → implementer (GREEN)
  └─ small mechanical change → inline
  │
  └─ coding-standards + verification-loop
  ▼
/review-pr <target>
  ├─ mandatory and diff-selected review lenses
  ├─ change-review
  ├─ security, when the selected risk lenses require it
  └─ implementer, for authorized fixes; broad or high-consequence changes are re-reviewed
  ▼
/ship
  ├─ commit-message-writer → commit → push
  ├─ pr-describer → create or refresh the PR
  ├─ watch CI; debugger → implementer when failures need correction
  ├─ review-pr comments mode → reply, resolve, and re-verify
  └─ report merge-ready
  ▼
"merge it"
  └─ merge only with explicit authority, green current-head CI, and no open threads
```

## Models

Each droid pins a model and reasoning effort suited to its job.

| Model | Role | Used by |
| --- | --- | --- |
| `gpt-5.6-sol` (xhigh) | Planning, repository investigation, root cause, and correctness review | `planner`, `deep-understanding`, `debugger`, `change-review`, `review-worker` |
| `gpt-5.6-terra` (high) | Implementation, testing, and precise config edits | `implementer`, `test-engineer`, `doc-generator` |
| `gpt-5.6-luna` (high/medium) | Triage and format-mechanical work | `quick-analysis`, `commit-message-writer` |
| `claude-opus-4-8` (xhigh/high) | Security, external research, prompt critique, and PR prose | `security`, `deep-research`, `prompt-optimizer`, `pr-describer` |


## Repository layout

```text
sagar-plugins/
├── .factory-plugin/
│   └── marketplace.json      # marketplace catalog
├── .github/workflows/
│   └── validate.yml          # structural checks and policy tests
├── docs/
│   └── WORKFLOW.md           # detailed workflow contract
├── scripts/
│   └── validate.mjs          # marketplace validator
└── plugins/
    ├── investigation/        # 4 research and debugging droids
    ├── practices/            # planning droid + 9 policy skills
    ├── build/                # 2 execution droids + implement/ship
    ├── review/               # 3 review droids + review-pr
    ├── synthesis/            # commit and PR prose droids
    ├── meta/                 # prompt audit/apply droids + loop skill
    └── guardrails/           # deterministic workflow hooks
```
