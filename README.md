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
| [`review`](./plugins/review/) | Droids: `change-review`, `security`; Skill: `review-fix` (+ `/review-fix` command) | quality |
| [`synthesis`](./plugins/synthesis/) | Droids: `pr-describer`, `commit-message-writer` | productivity |
| [`meta`](./plugins/meta/) | Droids: `prompt-optimizer`, `doc-generator`; Skill: `audit-and-apply-loop` | productivity |
| [`practices`](./plugins/practices/) | Skills: planning (`spec`, `tech-spec`, `architecture-scan`, `grilling`, `grill-me`, `discovering-unknowns`) + discipline (`agentic-engineering`, `tdd-workflow`, `coding-standards`, `verification-loop`) | productivity |
| [`build`](./plugins/build/) | Droids: `implementer`, `test-engineer`; Skill: `fix-pr` (+ `/fix-pr` command) | productivity |

Total: 12 droids, 13 skills, 2 commands. (CI recomputes these counts from the filesystem; see [Validation](#validation).)

## Concepts

- **Skills**: repeatable procedures the main agent runs inline. Markdown SOPs that Droid auto-loads when a task matches.
- **Droids**: sub-agents you delegate to. Each has a pinned model and a reasoning budget.

## Usage

The plugins compose into one delegation and procedure loop:

```
optionally discovering-unknowns → blind-spot pass first, when the territory is unfamiliar
  │
  ▼
spec / architecture-scan  → scope the work or rank refactor candidates
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
  └── review:          change-review + security (droids)
                       or review-fix (skill): review read-only, fix, verify, commit — ask before push
  │
  ▼
synthesis: pr-describer + commit-message-writer
```

A separate meta loop improves the droid prompts themselves: `prompt-optimizer` audits, `doc-generator` applies, governed by the `audit-and-apply-loop` skill.

## Evals

Prompt upgrades are checked against the golden-task pack in [`evals/golden-tasks/`](./evals/golden-tasks/). Critical goldens must all pass, and the overall pack must score at least 85% before a prompt rewrite is considered ready.

Run a task headlessly with [`scripts/run-golden-task.sh`](./scripts/run-golden-task.sh); score the transcript with the [`evals/golden-tasks/JUDGE.md`](./evals/golden-tasks/JUDGE.md) rubric prompt. Accepted outputs are stored under [`evals/baselines/`](./evals/baselines/) and diffed on the next run.

## Validation

`node scripts/validate.mjs` enforces the repo's structural invariants: manifest JSON validity and name/dir agreement, marketplace and plugin description equality, droid frontmatter (valid model IDs, per-model `reasoningEffort` compatibility, known tool IDs, output contract present), skill frontmatter (semver version), README counts vs the filesystem, resolvable cross-plugin `.md` references, and golden-task targets that exist. CI runs it on every push and PR; PRs additionally require a `plugin.json` version bump for any plugin whose files changed (`--require-bumps`).

## Versioning

One rule: any change under `plugins/<name>/` bumps that plugin's `plugin.json` version (semver). Skills additionally carry their own `version` frontmatter and bump it when their content changes. Droids version through their plugin only — droid frontmatter has no version field because `DroidValidator` only accepts documented keys. CI enforces the plugin-level bump on PRs.

## Models

Each droid is pinned to the right model for its job rather than "the best model" for everything, because different model families catch different things. No droid uses `inherit`: a pinned slug keeps a droid's output distribution independent of whatever model the parent session happens to run, and `reasoningEffort` is ignored under `inherit`. Every droid also pins `reasoningEffort` explicitly.

| Model | Tier | Used by |
| --- | --- | --- |
| `glm-5.2` (high) | Fast and cheap; triage and format-mechanical work | `quick-analysis`, `commit-message-writer` |
| `gpt-5.4` (high) | Strong reasoning; test writing | `test-engineer` |
| `gpt-5.5` (xhigh) | Highest-reasoning implementation tier | `implementer` |
| `gpt-5.4` (xhigh) | Deep reasoning; investigations, root-cause, security, prompt application | `deep-understanding`, `debugger`, `security`, `doc-generator` |
| `claude-opus-4-8` (xhigh) | Strong prompt critique and adherence diagnosis; deep external research | `prompt-optimizer`, `deep-research` |
| `glm-5.2` (max) | Different distribution at its max reasoning; strict last-gate correctness review that complements `gpt-5.4` | `change-review` |
| `claude-opus-4-8` (high) | Strongest natural prose; PR synthesis | `pr-describer` |

`glm-5.2` supports `off`, `high` (default), and `max` per the CLI's model registry (the docs page lags): the triage/format droids run its `high` default, `change-review` runs `max`. The validator's effort compatibility map is extracted from the CLI registry, not the docs.

### Fable-class models

Long-horizon models (`claude-fable-5`) earn their multiplier at the **orchestrator level**, where the unknowns work lives (`discovering-unknowns`, `spec`, `grilling`) — run the session there and the deep-tier review `worker`s inherit it for free. Fleet droids stay pinned to their cheaper complementary models. The one pin under trial is `implementer` (`gpt-5.5` at 2x vs `claude-fable-5` at 4x), decided by A/B on the golden pack:

```bash
scripts/run-golden-task.sh evals/golden-tasks/08-implementer-minimal-fix.md --judge --label a-gpt55
scripts/run-golden-task.sh evals/golden-tasks/08-implementer-minimal-fix.md --judge --label b-fable \
  --droid plugins/build/droids/implementer.md --model claude-fable-5 --effort xhigh
```

Adopt the swap only if the Fable variant wins the rubric on golden 08 **and** one real change-set unit, by enough to justify twice the cost.

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
    ├── review/               # 2 droids + 1 skill + 1 command
    ├── synthesis/            # 2 droids
    ├── meta/                 # 2 droids + 1 skill
    ├── practices/            # 10 skills
    └── build/                # 2 droids + 1 skill + 1 command
```
