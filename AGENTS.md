# sagar-plugins

A Factory plugin marketplace. The shipped artifact is prompts: 13 skills, 13 droids, and five
deterministic hooks. The markdown is the product, so treat prose edits as behavior changes.

## Gotchas

**Editing a skill or droid costs an eval re-baseline.** CI runs
`node scripts/validate-evals.mjs --require-fresh-baselines origin/<base>`, which fails when a file
a golden task targets changed without that task's baseline being re-accepted. Fix it with:

```bash
scripts/accept-baseline.sh evals/golden-tasks/<task>.md
```

That is three judged runs per touched task, so a few minutes and real spend. Before paying it, run
the free check: `python3 -m unittest discover -s plugins/guardrails/tests`. Its
`WorkflowPolicyContractTests` asserts that named rules still exist in named prose files and catches
most accidental deletions instantly. Note the gate compares committed HEAD against the base ref, so
an uncommitted prose edit will not trip it locally.

**Version bumps are enforced on PRs.** Any changed `plugin.json`, `SKILL.md`, or droid file needs
its version bumped. Check with `node scripts/validate.mjs --require-bumps origin/main`.

**Two vocabularies are permanently retired.** The `[review:*]` stage tags and
`[security:selected]` marker are gone. Reviewer fan-out is bounded by counted Task calls in
`plugins/guardrails/hooks/review_budget.py`, not by self-declared labels. `scripts/validate.mjs`
fails the build if either string reappears in tracked plugin markdown.

**Routing has exactly one canonical home:** `docs/WORKFLOW.md`, marked
`<!-- routing-table:canonical -->`. A second routing table in tracked markdown fails the build.

**`coding-standards/` topic files are knowledge, not process.** They carry engineering opinion and
are exempt from prose compression. Do not shorten them to hit a line target.

**Transcripts under `evals/baselines/transcripts/` are local only.** This repository is public and
transcripts are model output from one machine. Only the verdict JSON is committed.

**Hook coverage floor is 87%** over `plugins/guardrails/hooks`, enforced in CI.

## Adding a control

Prefer a control that verifies a fact outside the agent's own output: a file hash, a git revision,
a live API response, an exit status. Controls that police a label the agent writes, or that predict
which risks a diff carries, have failed here before and were removed.
