# sagar-plugins

> Multi-model droid toolkit and engineering-discipline skills for [Factory](https://factory.ai), in six focused plugins.

Sagar's personal Factory plugins marketplace. Each plugin is independently installable; install all six for the full delegation and procedure workflow.

## Install

Add the marketplace, then install the plugins you want:

```bash
droid plugin marketplace add https://github.com/factory-sagar/sagar-plugins

# Install all six for the full toolkit:
droid plugin install investigation@sagar-plugins
droid plugin install review@sagar-plugins
droid plugin install synthesis@sagar-plugins
droid plugin install meta@sagar-plugins
droid plugin install practices@sagar-plugins
droid plugin install build@sagar-plugins
```

Or browse interactively with `/plugins`.

## Plugins

| Plugin | Contents | Category |
| --- | --- | --- |
| [`investigation`](./plugins/investigation/) | Droids: `quick-analysis`, `deep-understanding`, `deep-research`, `debugger` | research |
| [`review`](./plugins/review/) | Droids: `change-review`, `security` | quality |
| [`synthesis`](./plugins/synthesis/) | Droids: `pr-describer`, `commit-message-writer` | productivity |
| [`meta`](./plugins/meta/) | Droids: `prompt-optimizer`, `doc-generator`; Skill: `audit-and-apply-loop` | productivity |
| [`practices`](./plugins/practices/) | Skills: planning (`spec`, `tech-spec`, `architecture-scan`, `grilling`, `grill-me`) + discipline (`agentic-engineering`, `tdd-workflow`, `coding-standards`, `verification-loop`) | productivity |
| [`build`](./plugins/build/) | Droids: `implementer`, `test-engineer`; Skill: `fix-pr` (+ `/fix-pr` command) | productivity |

Total: 12 droids, 11 skills, 1 command.

## Concepts

- **Skills**: repeatable procedures the main agent runs inline. Markdown SOPs that Droid auto-loads when a task matches.
- **Droids**: sub-agents you delegate to. Each has a pinned model and a reasoning budget.

## Usage

The plugins compose into one delegation and procedure loop:

```
spec / architecture-scan  → scope the work or rank refactor candidates
  │
  ├── optionally grilling  → stress-test the plan
  └── optionally tech-spec → typed contracts, seams, call stacks
  │
  ▼
(for each unit)
  ├── investigation:   quick-analysis / deep-understanding / deep-research
  ├── implementation:  tdd-workflow + coding-standards (skills the main agent runs)
  ├── verification:    verification-loop (skill)
  └── review:          change-review + security (droids)
  │
  ▼
synthesis: pr-describer + commit-message-writer
```

A separate meta loop improves the droid prompts themselves: `prompt-optimizer` audits, `doc-generator` applies, governed by the `audit-and-apply-loop` skill.

## Evals

Prompt upgrades are checked against the golden-task pack in [`evals/golden-tasks/`](./evals/golden-tasks/). Critical goldens must all pass, and the overall pack must score at least 85% before a prompt rewrite is considered ready.

## Models

Each droid is pinned to the right model for its job rather than "the best model" for everything, because different model families catch different things.

| Model | Tier | Used by |
| --- | --- | --- |
| `glm-5.2` | Fast and cheap; triage and format-mechanical work | `quick-analysis`, `commit-message-writer` |
| `gpt-5.4` (high) | Strong reasoning; test writing | `test-engineer` |
| `gpt-5.5` (xhigh) | Highest-reasoning implementation tier | `implementer` |
| `gpt-5.4` (xhigh) | Deep reasoning; investigations, root-cause, security, prompt application | `deep-understanding`, `debugger`, `security`, `doc-generator` |
| `claude-opus-4-8` (xhigh) | Strong prompt critique and adherence diagnosis | `prompt-optimizer` |
| `glm-5.2` (xhigh) | Different distribution at max reasoning; strict last-gate correctness review that complements `gpt-5.4` | `change-review` |
| `inherit` (Claude Opus) | Strongest natural prose; synthesis and external research | `pr-describer`, `deep-research` |

## Layout

```
sagar-plugins/
├── .factory-plugin/
│   └── marketplace.json
├── evals/
│   └── golden-tasks/        # prompt regression tasks and rubrics
└── plugins/
    ├── investigation/        # 4 droids
    ├── review/               # 2 droids
    ├── synthesis/            # 2 droids
    ├── meta/                 # 2 droids + 1 skill
    ├── practices/            # 9 skills
    └── build/                # 2 droids + 1 skill + 1 command
```
