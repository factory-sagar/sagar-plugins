# sagar-plugins

Sagar's personal [Factory](https://factory.ai) plugins marketplace.

Multi-model droid toolkit + engineering-discipline skills, split into five focused plugins. Each plugin is independently installable; install all five for the full delegation + procedure experience.

## Concepts

- **Skills** = repeatable flows. Markdown SOPs Droid auto-loads when a task matches.
- **Droids** = sub-agents you delegate to. Each has a model and a reasoning budget.

## Install

Add the marketplace and install the plugins you want:

```bash
droid plugin marketplace add https://github.com/factory-sagar/sagar-plugins

# Install all five for the full toolkit:
droid plugin install investigation@sagar-plugins
droid plugin install review@sagar-plugins
droid plugin install synthesis@sagar-plugins
droid plugin install meta@sagar-plugins
droid plugin install practices@sagar-plugins
```

Or browse via the interactive UI:

```
/plugins
```

## Plugins

| Plugin | Droids | Skills | Marketplace category |
| --- | --- | --- | --- |
| [`investigation`](./plugins/investigation/) | `quick-analysis`, `deep-understanding`, `deep-research` | — | research |
| [`review`](./plugins/review/) | `change-review`, `security` | — | quality |
| [`synthesis`](./plugins/synthesis/) | `pr-describer`, `commit-message-writer` | — | productivity |
| [`meta`](./plugins/meta/) | `prompt-optimizer`, `doc-generator` | `audit-and-apply-loop` | productivity |
| [`practices`](./plugins/practices/) | — | `spec`, `agentic-engineering`, `tdd-workflow`, `coding-standards`, `verification-loop` | productivity |

**Total: 9 droids + 6 skills.**

## The full delegation + procedure loop

```
spec                  → defines what done looks like AND decomposes work into droid-tagged units
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

Plus a meta loop for the droid prompts themselves: `prompt-optimizer` audits, `doc-generator` applies, governed by the `audit-and-apply-loop` skill.

## Why split into focused plugins?

Different jobs, different cadences. You may want `review` and `synthesis` on every workstation but `meta` only when authoring agentic configs. Splitting also surfaces each plugin under its proper marketplace category instead of bundling everything under one.

The droids and skills compose across plugins. Install everything for the full experience.

## Why multiple models

Different model families catch different things:

- **`glm-5`** (fast/cheap) — triage and format-mechanical work (`quick-analysis`, `commit-message-writer`).
- **`gpt-5.4 xhigh`** (deep reasoning) — investigations and audits (`deep-understanding`, `security`, `prompt-optimizer`, `doc-generator`).
- **`kimi-2.6 xhigh`** (different distribution) — catches regulatory / consent / subtle correctness issues `gpt-5.4` misses (`change-review`).
- **`inherit` (Claude Opus)** — strongest natural prose; synthesis and external research (`pr-describer`, `deep-research`).

Delegate to the right model for the job, not "the best model" for everything.

## Roadmap

- **Phase 0** ✅ — marketplace structure, three baseline droids.
- **Phase 1** ✅ — six new droids across investigation / review / synthesis / meta with deliberate per-droid model assignment.
- **Phase 1.5** ✅ — split into four focused plugins by category.
- **Phase 2** ✅ — skills layer: `practices` plugin (5 skills) + `audit-and-apply-loop` skill in `meta`. Lifted/adapted from [`affaan-m/ECC`](https://github.com/affaan-m/ECC), de-duplicated against [`Factory-AI/factory-plugins`](https://github.com/Factory-AI/factory-plugins), generalized away from any specific harness.
- **Phase 3+** — author additional original skills as patterns emerge from real usage.

## Layout

```
sagar-plugins/
├── .factory-plugin/
│   └── marketplace.json
└── plugins/
    ├── investigation/   # 3 droids
    ├── review/          # 2 droids
    ├── synthesis/       # 2 droids
    ├── meta/            # 2 droids + 1 skill
    └── practices/       # 5 skills
```
