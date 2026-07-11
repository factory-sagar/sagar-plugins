# sagar-plugins

> Deterministic engineering workflows, policy skills, specialist droids, and delivery
> guardrails for [Factory](https://factory.ai).

Four public skills provide the operator surface: `spec`, `implement`, `review-pr`, and
`ship`. Model-invoked policy skills and specialist droids supply the method behind those
short requests.

## Install

Add the marketplace, then install the plugins you want:

```bash
droid plugin marketplace add https://github.com/factory-sagar/sagar-plugins

# Install the complete toolkit:
droid plugin install investigation@sagar-plugins
droid plugin install review@sagar-plugins
droid plugin install synthesis@sagar-plugins
droid plugin install meta@sagar-plugins
droid plugin install practices@sagar-plugins
droid plugin install build@sagar-plugins
droid plugin install guardrails@sagar-plugins
```

Or browse interactively with `/plugins`.

## Plugins

| Plugin | Contents | Category |
| --- | --- | --- |
| [`investigation`](./plugins/investigation/) | Droids: `quick-analysis`, `deep-understanding`, `deep-research`, `debugger` | research |
| [`review`](./plugins/review/) | Droids: `change-review`, `security`, `review-worker`; public skill: `review-pr` | quality |
| [`synthesis`](./plugins/synthesis/) | Droids: `pr-describer`, `commit-message-writer` | productivity |
| [`meta`](./plugins/meta/) | Droids: `prompt-optimizer`, `doc-generator`; Skill: `audit-and-apply-loop` | productivity |
| [`practices`](./plugins/practices/) | Droid: `planner`; public skill: `spec`; model-invoked planning and engineering policy | productivity |
| [`build`](./plugins/build/) | Droids: `implementer`, `test-engineer`; public skills: `implement`, `ship` | productivity |
| [`guardrails`](./plugins/guardrails/) | Four-intent router, push policy, delivery ledger, and current-head completion gate | quality |

Total: 14 droids, 13 skills, 0 commands. Only the four public skills appear in the slash
menu; internal policy skills remain model-invoked.

## Concepts

- **Public skills**: four operator entry points. Short requests receive the full method;
  detailed prompts add constraints and automatically trigger deeper design work.
- **Policy skills**: model-invoked reference and procedure bundles hidden from the slash menu.
- **Droids**: sub-agents you delegate to. Each has a pinned model and a reasoning budget.
- **Hooks**: deterministic controls that run independently of model judgment.

## Usage

**[docs/WORKFLOW.md](./docs/WORKFLOW.md)** defines one entry point per stage, explicit
authority boundaries, and named owners for verification, PR maintenance, CI, and comments.
Blocked stages still return to the operator with the unresolved evidence.

The plugins compose into one delegation and procedure loop:

```
optionally discovering-unknowns → blind-spot pass first, when the territory is unfamiliar
  │
  ▼
spec                    → plan the work; detailed design intent automatically adds
  │                       unknown discovery, architecture scan, and typed tech spec
  │
  ├── optionally grilling  → stress-test the plan
  └── optionally tech-spec → typed contracts, seams, call stacks
  │
  ▼
(for each unit)
  ├── investigation:   quick-analysis / deep-understanding / deep-research
  ├── implementation:  tdd-workflow + coding-standards (skills the main agent runs)
  │                    workers carry the Deviations contract (discovering-unknowns)
  ├── verification:    verification-loop (skill)
  └── review:          review-pr selects mandatory + diff-driven lenses, then delegates
                       to change-review and security as required
  │
  ▼
synthesis: pr-describer + commit-message-writer
  │
  ▼
ship (skill): commit → push → PR body per template → CI watch → resolve threads → merge-ready
```

A separate meta loop improves the droid prompts themselves: `prompt-optimizer` audits, `doc-generator` applies, governed by the `audit-and-apply-loop` skill.

## Evals

Prompt upgrades are checked against the golden-task pack in
[`evals/golden-tasks/`](./evals/golden-tasks/) and the unforced routing corpus in
[`evals/routing/`](./evals/routing/). [`evals/policy.json`](./evals/policy.json)
defines critical quality, routing, false-positive, repetition, cost, and latency gates.

Run a task headlessly with [`scripts/run-golden-task.sh`](./scripts/run-golden-task.sh).
Score captured routing results with [`scripts/eval-routing.mjs`](./scripts/eval-routing.mjs).
Model pins are mirrored in [`evals/model-assignments.json`](./evals/model-assignments.json)
and link to versioned decision records.

## Validation

`node scripts/validate.mjs` enforces manifests, droid frontmatter, the four-skill public
surface, model-assignment parity and evidence links, routing-case integrity, policy bounds,
README counts, cross-plugin references, golden targets, and plugin/skill version bumps.

## Versioning

One rule: any change under `plugins/<name>/` bumps that plugin's `plugin.json` version (semver). Skills additionally carry their own `version` frontmatter and bump it when their content changes. Droids version through their plugin only — droid frontmatter has no version field because `DroidValidator` only accepts documented keys. CI enforces the plugin-level bump on PRs.

## Models

Each droid pins a model and reasoning effort, but assignments are provisional until they
clear repeated role-specific evaluations. Family diversity is useful evidence, not a
substitute for measured quality.

| Model | Role | Used by |
| --- | --- | --- |
| `gpt-5.6-sol` (xhigh) | Heavy planning, investigation, and root cause | `planner`, `deep-understanding`, `debugger` |
| `gpt-5.6-terra` (high) | Implementation, tests, and precise config edits | `implementer`, `test-engineer`, `doc-generator` |
| `gpt-5.6-luna` (high/medium) | Triage and format-mechanical work | `quick-analysis`, `commit-message-writer` |
| `gpt-5.2` (xhigh) | Correctness review incumbent | `change-review`, `review-worker` |
| `claude-opus-4-8` (xhigh/high) | Security, research, prompt critique, and PR prose | `security`, `deep-research`, `prompt-optimizer`, `pr-describer` |

[`evals/model-assignments.json`](./evals/model-assignments.json) is the machine-readable
source of truth for current assignments and evidence status.

## Layout

```
sagar-plugins/
├── .factory-plugin/
│   └── marketplace.json
├── .github/
│   └── workflows/            # validate.yml — structural invariants + version bumps
├── scripts/                  # validate.mjs, run-golden-task.sh
├── evals/
│   ├── golden-tasks/         # prompt regression tasks, rubrics, JUDGE.md
│   └── baselines/            # accepted golden-task outputs (regression reference)
└── plugins/
    ├── investigation/        # 4 droids
    ├── review/               # 3 droids + 1 skill
    ├── synthesis/            # 2 droids
    ├── meta/                 # 2 droids + 1 skill
    ├── practices/            # 1 droid + 9 skills (1 public)
    ├── build/                # 2 droids + 2 public skills
    └── guardrails/           # deterministic delivery hooks
```
