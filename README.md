# sagar-skills

Personal [Factory](https://factory.ai) droids and skills.

## Contents

**Droids** (`.factory/droids/`)
- `deep-analysis` — evidence-backed repo and agentic-config analysis
- `change-review` — strict reviewer for diffs, commits, or scoped files

**Skills** (`.factory/skills/`)
- `simplify` — parallel review for reuse, quality, and efficiency, then fix
- `follow-up-on-pr` — rebase, address feedback, run checks, push, reply

## Install

Global:
```bash
cp -R .factory/droids/* ~/.factory/droids/
cp -R .factory/skills/*  ~/.factory/skills/
```

Project-local: copy `.factory/` into your project root.

Droids pin `model: gpt-5.4` — change to `inherit` in the front-matter if you don't have access.
