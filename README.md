# sagar-plugins

Sagar's personal [Factory](https://factory.ai) plugins marketplace.

## Concepts

- **Skills** = repeatable flows. Markdown SOPs Droid auto-loads when a task matches.
- **Droids** = sub-agents you delegate to. Each has a model and a reasoning budget.

This marketplace ships droids today. Skills come in a later phase.

## Install

Add the marketplace and install the plugin:

```bash
droid plugin marketplace add https://github.com/factory-sagar/sagar-plugins
droid plugin install sagar@sagar-plugins
```

Or browse via the interactive UI:

```
/plugins
```

## Plugins

| Plugin | What you get |
| --- | --- |
| [`sagar`](./plugins/sagar/) | Three analysis and review droids: `quick-analysis`, `deep-understanding`, `change-review` |

## Roadmap

- **Phase 0** (current) — droid toolkit, marketplace shape, no skills.
- **Phase 1** — mine [`affaan-m/ECC`](https://github.com/affaan-m/ECC/tree/main/skills) for skills worth lifting, dedupe against `Factory-AI/factory-plugins`.
- **Phase 2+** — split `sagar` into focused plugins (e.g. `sagar-research`, `sagar-ops`) once we have meaningful skill clusters.

## Layout

```
sagar-plugins/
├── .factory-plugin/
│   └── marketplace.json
└── plugins/
    └── sagar/
        ├── .factory-plugin/plugin.json
        ├── droids/
        │   ├── quick-analysis.md
        │   ├── deep-understanding.md
        │   └── change-review.md
        └── README.md
```
