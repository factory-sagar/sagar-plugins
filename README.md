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
| [`sagar`](./plugins/sagar/) | Nine multi-model droids: `quick-analysis`, `deep-understanding`, `deep-research`, `change-review`, `security`, `pr-describer`, `commit-message-writer`, `prompt-optimizer`, `doc-generator` |

## Roadmap

- **Phase 0** ✅ — marketplace structure, three baseline droids.
- **Phase 1** ✅ — six new droids across investigation / review / synthesis / meta categories with deliberate per-droid model assignment (`glm-5`, `gpt-5.4`, `kimi-2.6`, Claude via `inherit`).
- **Phase 2** — skills layer: mine [`affaan-m/ECC`](https://github.com/affaan-m/ECC/tree/main/skills) for repeatable flows worth lifting, dedupe against `Factory-AI/factory-plugins`.
- **Phase 3+** — split `sagar` into focused plugins (e.g. `sagar-investigation`, `sagar-review`, `sagar-synthesis`) once we cross ~12 droids.

## Layout

```
sagar-plugins/
├── .factory-plugin/
│   └── marketplace.json
└── plugins/
    └── sagar/
        ├── .factory-plugin/plugin.json
        ├── droids/
        │   ├── quick-analysis.md          # glm-5
        │   ├── deep-understanding.md      # gpt-5.4 xhigh
        │   ├── deep-research.md           # inherit (Claude) xhigh
        │   ├── change-review.md           # kimi-2.6 xhigh
        │   ├── security.md                # gpt-5.4 xhigh
        │   ├── pr-describer.md            # inherit (Claude) high
        │   ├── commit-message-writer.md   # glm-5
        │   ├── prompt-optimizer.md        # gpt-5.4 xhigh
        │   └── doc-generator.md           # gpt-5.4 xhigh
        └── README.md
```
