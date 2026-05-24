# sagar-plugins

Sagar's personal [Factory](https://factory.ai) plugins marketplace.

Multi-model droid toolkit split into four focused plugins. Each plugin is independently installable; install all four for the full delegation experience.

## Concepts

- **Skills** = repeatable flows. Markdown SOPs Droid auto-loads when a task matches.
- **Droids** = sub-agents you delegate to. Each has a model and a reasoning budget.

This marketplace ships droids today (9 of them). Skills come in a later phase.

## Install

Add the marketplace and install the plugins you want:

```bash
droid plugin marketplace add https://github.com/factory-sagar/sagar-plugins

# Install all four for the full toolkit:
droid plugin install investigation@sagar-plugins
droid plugin install review@sagar-plugins
droid plugin install synthesis@sagar-plugins
droid plugin install meta@sagar-plugins
```

Or browse via the interactive UI:

```
/plugins
```

## Plugins

| Plugin | Droids | Marketplace category |
| --- | --- | --- |
| [`investigation`](./plugins/investigation/) | `quick-analysis`, `deep-understanding`, `deep-research` | research |
| [`review`](./plugins/review/) | `change-review`, `security` | quality |
| [`synthesis`](./plugins/synthesis/) | `pr-describer`, `commit-message-writer` | productivity |
| [`meta`](./plugins/meta/) | `prompt-optimizer`, `doc-generator` | productivity |

## Why split into four plugins?

Different jobs, different cadences. You may want `review` and `synthesis` on every workstation but `meta` only when you're authoring agentic configs. Splitting also surfaces each plugin under its proper marketplace category instead of bundling everything under one.

The droids still compose across plugins — see each plugin's README for hand-off chains. Install all four for the full delegation experience.

## Why multiple models

Different model families catch different things:

- **`glm-5`** (fast/cheap) — triage and format-mechanical work (`quick-analysis`, `commit-message-writer`).
- **`gpt-5.4 xhigh`** (deep reasoning) — investigations and audits (`deep-understanding`, `security`, `prompt-optimizer`, `doc-generator`).
- **`kimi-2.6 xhigh`** (different distribution) — catches regulatory / consent / subtle correctness issues `gpt-5.4` misses (`change-review`).
- **`inherit` (Claude Opus)** — strongest natural prose; synthesis and external research (`pr-describer`, `deep-research`).

Delegate to the right model for the job, not "the best model" for everything.

## Roadmap

- **Phase 0** ✅ — marketplace structure, three baseline droids.
- **Phase 1** ✅ — six new droids across investigation / review / synthesis / meta categories with deliberate per-droid model assignment.
- **Phase 1.5** ✅ — split into four focused plugins by category.
- **Phase 2** — skills layer: mine [`affaan-m/ECC`](https://github.com/affaan-m/ECC/tree/main/skills) for repeatable flows worth lifting, dedupe against `Factory-AI/factory-plugins`.

## Layout

```
sagar-plugins/
├── .factory-plugin/
│   └── marketplace.json
└── plugins/
    ├── investigation/
    │   ├── .factory-plugin/plugin.json
    │   ├── droids/
    │   │   ├── quick-analysis.md       # glm-5
    │   │   ├── deep-understanding.md   # gpt-5.4 xhigh
    │   │   └── deep-research.md        # inherit (Claude) xhigh
    │   └── README.md
    ├── review/
    │   ├── .factory-plugin/plugin.json
    │   ├── droids/
    │   │   ├── change-review.md        # kimi-2.6 xhigh
    │   │   └── security.md             # gpt-5.4 xhigh
    │   └── README.md
    ├── synthesis/
    │   ├── .factory-plugin/plugin.json
    │   ├── droids/
    │   │   ├── pr-describer.md         # inherit (Claude) high
    │   │   └── commit-message-writer.md  # glm-5
    │   └── README.md
    └── meta/
        ├── .factory-plugin/plugin.json
        ├── droids/
        │   ├── prompt-optimizer.md     # gpt-5.4 xhigh
        │   └── doc-generator.md        # gpt-5.4 xhigh
        └── README.md
```
