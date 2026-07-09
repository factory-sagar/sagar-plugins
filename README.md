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
| [`review`](./plugins/review/) | Droids: `change-review`, `security`, `review-worker`; Skill: `review-fix` (`/review-fix`) | quality |
| [`synthesis`](./plugins/synthesis/) | Droids: `pr-describer`, `commit-message-writer` | productivity |
| [`meta`](./plugins/meta/) | Droids: `prompt-optimizer`, `doc-generator`; Skill: `audit-and-apply-loop` | productivity |
| [`practices`](./plugins/practices/) | Droid: `planner`; Skills: planning (`spec` (`/spec`), `tech-spec`, `architecture-scan`, `grilling`, `grill-me`, `discovering-unknowns`) + discipline (`agentic-engineering`, `tdd-workflow`, `coding-standards`, `verification-loop`) | productivity |
| [`build`](./plugins/build/) | Droids: `implementer`, `test-engineer`; Skills: `fix-pr` (`/fix-pr`), `implement` (`/implement`), `ship` (`/ship`) | productivity |

Total: 14 droids, 15 skills, 0 commands — skills register their own slash entry points, so there are no separate command files. (CI recomputes these counts from the filesystem; see [Validation](#validation).)

## Concepts

- **Skills**: repeatable procedures the main agent runs inline. Markdown SOPs that Droid auto-loads when a task matches. Each skill also registers `/skill-name` as a deterministic entry point, so no separate command files are needed.
- **Droids**: sub-agents you delegate to. Each has a pinned model and a reasoning budget.

## Usage

The plugins compose into one delegation and procedure loop:

```
optionally discovering-unknowns → blind-spot pass first, when the territory is unfamiliar
  │
  ▼
spec / architecture-scan  → scope the work or rank refactor candidates
  │                         (spec delegates heavy planning to the planner droid — fable-5)
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
  │
  ▼
ship (skill): commit → push → PR body per template → CI watch → resolve threads → merge-ready
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

The fleet follows a **three-family pipeline** (adopted 2026-07-09): GLM writes, GPT-5.5
reviews, Fable plans and judges. No line of code is written and reviewed by the same
model family, which moves the "different families catch different bugs" principle from
inside the review step to the pipeline level.

| Model | Role | Used by |
| --- | --- | --- |
| `claude-fable-5` (xhigh) | Plan & judge — long-horizon reasoning where the unknowns live | `planner`, `prompt-optimizer` |
| `glm-5.2` (max) | Do — implementation workloads | `implementer` |
| `glm-5.2` (high) | Do — triage and format-mechanical work | `quick-analysis`, `commit-message-writer` |
| `gpt-5.5` (high) | Review & diagnose | `change-review`, `review-worker`, `test-engineer`, `doc-generator` |
| `gpt-5.5` (xhigh) | Review & diagnose — attack-path and root-cause depth | `security`, `debugger` |
| `gpt-5.4` (xhigh) | Deep repo investigation | `deep-understanding` |
| `claude-opus-4-8` (xhigh) | Deep external research | `deep-research` |
| `claude-opus-4-8` (high) | Strongest natural prose; PR synthesis | `pr-describer` |

`glm-5.2` supports `off`, `high` (default), and `max` per the CLI's model registry (the docs page lags): the triage/format droids run its `high` default, `implementer` runs `max`. The validator's effort compatibility map is extracted from the CLI registry, not the docs.

**Revert trigger:** `implementer` moved fable-5 → glm-5.2 max under this strategy despite the
2026-07-04 A/B (fable won on convention fit and Deviations discipline). The monthly usage
report's correction-rate trend arbitrates: if corrections spike on implementation work, the
pin reverts to `claude-fable-5` (xhigh). Plan-tagged `risk: high` units should be delegated
to a fable-tier session or worker regardless of the default pin.

### Fable-class models

Long-horizon models (`claude-fable-5`) earn their multiplier where the unknowns work lives. Since 2026-07-09 that is the **`planner` droid** (delegated by the `spec` skill) rather than whole orchestrator sessions: sessions run cheap, and Fable spends its multiplier only on planning and judgement. Deep-tier review subagents no longer inherit the session model — they run as the pinned `review-worker`.

A/B record (2026-07-04): `implementer` on `claude-fable-5` beat `gpt-5.5` on convention fit (schema-level clamp matching sibling routes), verification rigor (full domain suite + strict lint vs one test file), and Deviations discipline (evidence-anchored log vs a silent deviation), with `change-review` returning zero findings on both diffs. The 2026-07-09 three-family strategy still moved `implementer` to `glm-5.2` (max) for cost, accepting the trade consciously — the monthly correction-rate report is the revert trigger, and `claude-fable-5` (xhigh) is the recorded revert pin.

**Model A/Bs for droids must run in-session, not through the runner**: `droid exec` exposes no Task tool, so an exec session cannot spawn pinned droids — a droid-targeted golden under `scripts/run-golden-task.sh` measures contract adherence of the exec session model, not the pinned droid. To A/B a droid's model: write a temporary variant (e.g. `implementer-fable`) into the working repo's `.factory/droids/`, run both legs from a live session via the Task tool against isolated scratch dirs or worktrees, judge with `evals/golden-tasks/JUDGE.md`, and have `change-review` verdict both diffs.

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
    ├── practices/            # 1 droid + 10 skills
    └── build/                # 2 droids + 3 skills
```
