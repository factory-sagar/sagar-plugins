# Repository Guidelines

## Project Structure & Module Organization

This repository ships a Factory plugin marketplace. The product is prompt and configuration
content, so treat Markdown edits as behavior changes. Plugins live in `plugins/<name>/`; skills use
`skills/<skill>/SKILL.md`, droids use `droids/*.md`, and manifests are in
`.factory-plugin/plugin.json`. Deterministic hooks and their Python tests live under
`plugins/guardrails/`. Marketplace metadata is in `.factory-plugin/`, workflow policy is in
`docs/WORKFLOW.md`, and golden-task definitions and accepted verdicts are in `evals/`.

## Build, Test, and Development Commands

There is no build step or package installation. Run these checks from the repository root:

```bash
node scripts/validate.mjs
node scripts/validate-evals.mjs
node --test scripts/eval-routing.test.mjs scripts/compare-baseline.test.mjs scripts/validate-evals.test.mjs scripts/validate.test.mjs
python3 -m unittest discover -s plugins/guardrails/tests -v
python3 -m py_compile plugins/guardrails/hooks/*.py
```

CI also enforces 87% hook coverage. For a pull-request comparison, run
`node scripts/validate.mjs --require-bumps origin/main`. Changing a skill or droid requires
re-accepting each affected golden task with
`scripts/accept-baseline.sh evals/golden-tasks/<task>.md`.

## Coding Style & Naming Conventions

Preserve existing frontmatter, JSON formatting, and directory naming. Write prompt instructions
directly and keep policy terminology consistent with nearby files. Keep cross-plugin routing only
in `docs/WORKFLOW.md`; do not add another routing table. `coding-standards/` topic files are
reference knowledge, not process prose, so do not compress them mechanically. When adding a hook
control, prefer independently verifiable evidence such as an exit status or file hash.

## Testing Guidelines

Use `test_*.py` for guardrail tests and `*.test.mjs` for Node validators. Add or update tests with
hook and validator changes, then run the full command set above. Generated runs, results, and
baseline transcripts are local artifacts; commit accepted verdict JSON only.

## Commit & Pull Request Guidelines

Follow the established Conventional Commit style, for example
`feat(guardrails): add policy check`, `fix(review): handle empty diff`, or `chore: refresh
metadata`. Bump the owning plugin version when changing its manifest, skill, or droid. PRs should
state the behavior change, rationale, validation performed, and any required eval baseline updates.
