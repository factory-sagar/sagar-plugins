# sagar-plugins

A modular [Factory](https://factory.ai) plugin marketplace for taking engineering work from
an idea to a reviewed, merge-ready change.

The operator-facing workflow has four entry points:

```text
spec → implement → review-pr → ship
```

Behind them are specialist droids for investigation, planning, implementation, testing,
review, security, prompt work, and release prose. Deterministic hooks enforce safe pushes
and complete delivery.

**At a glance:** 7 plugins, 14 droids, 13 skills, 4 public workflows, and 1 guarded
idea-to-merge path.

## Quick start

Add the marketplace:

```bash
droid plugin marketplace add https://github.com/factory-sagar/sagar-plugins
```

Install the complete toolkit:

```bash
droid plugin install investigation@sagar-plugins
droid plugin install review@sagar-plugins
droid plugin install synthesis@sagar-plugins
droid plugin install meta@sagar-plugins
droid plugin install practices@sagar-plugins
droid plugin install build@sagar-plugins
droid plugin install guardrails@sagar-plugins
```

You can also browse and install individual plugins with `/plugins`.

Install individual plugins when you only need their droids or a standalone workflow. The
complete public workflows call across plugin boundaries:

| Workflow | Required plugins | Useful companions |
| --- | --- | --- |
| `spec` | `practices` | `investigation` for deeper repository or external research |
| `implement` | `build`, `practices` | `review` for the post-verification gate |
| `review-pr` | `review` | `build` for fixes, `practices` for design review, `investigation` for failure debugging |
| `ship` | `build`, `synthesis`, `review` | `investigation` for non-obvious CI failures |

Install the full toolkit for the end-to-end lifecycle.

## The four public workflows

Only these skills appear as public slash commands. Short natural-language requests such as
"plan this", "implement U2", "review PR 42", and "push this" select the same workflows when
the guardrails plugin is installed.

| Entry point | Owns | Typical result |
| --- | --- | --- |
| `/spec <request>` | Scope, evidence gathering, architecture decisions, and decomposition | A decisions-first plan with acceptance criteria and agent-sized units |
| `/implement <task or unit>` | Test-first execution, approved change sets, and local verification | A verified local change ready for review |
| `/review-pr <target>` | Correctness review, risk-selected security review, fixes, comments, and explicit authority | Findings or the strongest explicitly authorized reviewed outcome |
| `/ship` | Commit, push, PR maintenance, CI watch, and thread closure | A current, green, merge-ready PR |

Plain review stays read-only. Fixing, approving, pushing, and merging each require wording
that grants that authority. `/ship` does not merge unless the request explicitly says to
merge and every delivery gate passes.

## Core engineering flow

[`docs/WORKFLOW.md`](./docs/WORKFLOW.md) is the detailed workflow contract. The main path is:

```text
IDEA
  │
  ▼
/spec
  ├─ planner, the default path for evidence-backed decisions and executable units
  ├─ discovering-unknowns, before planning unfamiliar or taste-shaped work
  ├─ architecture-scan, first when the question is ownership or code placement
  ├─ grilling, when the current plan still has a major unresolved decision
  └─ tech-spec, when an approved plan needs typed contracts and call stacks
  │
  ▼ operator approves the plan
/implement <unit>
  ├─ approved change set → implementer
  ├─ new behavior → tdd-workflow → test-engineer (RED) → implementer (GREEN)
  └─ small mechanical change → inline
  │
  └─ coding-standards + verification-loop
  ▼
/review-pr <target>
  ├─ mandatory and diff-selected review lenses
  ├─ change-review
  ├─ security, when the selected risk lenses require it
  └─ implementer, for authorized fixes; broad or high-consequence changes are re-reviewed
  ▼
/ship
  ├─ commit-message-writer → commit → push
  ├─ pr-describer → create or refresh the PR
  ├─ watch CI; debugger → implementer when failures need correction
  ├─ review-pr comments mode → reply, resolve, and re-verify
  └─ report merge-ready
  ▼
"merge it"
  └─ merge only with explicit authority, green current-head CI, and no open threads
```

Factory's built-in `worker` may execute scoped units inside these workflows. It is not a
plugin in this marketplace.

## Common flows

### Plan an architecture change

```text
/spec <request>
  → discovering-unknowns, if the territory or criteria are unclear
  → architecture-scan, if the question is ownership or code placement
  → planner
  → grilling, if a major decision remains open
  → tech-spec, if the approved plan needs typed contracts and call stacks
  → approved implementation units
```

Use this path when the work changes ownership, boundaries, state, persistence, or failure
contracts. Small, well-understood changes skip the extra design stages.

### Build a feature with TDD

```text
/implement <unit>
  → tdd-workflow
  → test-engineer writes a failing behavior test
  → implementer makes the smallest passing change
  → optional refactor under the regression net
  → verification-loop
  → review-pr
```

### Diagnose and fix a bug

```text
failing behavior
  → debugger reproduces and proves the root cause
  → test-engineer pins the regression
  → implementer applies the fix plan
  → verification-loop
  → review-pr
```

`quick-analysis` handles fast repository triage, `deep-understanding` handles broad
repository or architecture questions, and `deep-research` handles questions that require
external sources.

### Review and land a change

```text
/review-pr <PR, branch, commit, or staged diff>
  → select review depth and risk lenses
  → change-review
  → security, when relevant
  → reconcile findings
  → fix, only when authorized
  → final-head re-review for broad or high-consequence changes
  → /ship
  → commit, push, PR body, CI, comments, merge-ready
```

Existing PR comments are inputs to the review, not a separate cleanup step. Comments mode
triages every thread, applies valid fixes, replies, resolves threads, and waits for green CI.

### Improve a droid or skill

```text
capture the current behavior
  → audit-and-apply-loop
  → prompt-optimizer audits the prompt
  → orchestrator selects findings under the loop's decision rule
  → doc-generator applies the smallest approved edits
  → rerun the same case and compare
```

Use `deep-understanding` instead of `prompt-optimizer` for marketplace-wide ownership,
plugin boundaries, or model-assignment questions.

## Plugin catalog

### [`investigation`](./plugins/investigation/) · research

Builds evidence before planning or fixing.

| Droid | Purpose |
| --- | --- |
| `quick-analysis` | Fast repository triage: stack, structure, entry points, anomalies, and the right next droid |
| `deep-understanding` | Thorough repository, subsystem, architecture, or agentic-config investigation |
| `deep-research` | External research with cited web evidence |
| `debugger` | Reproduce failures, test hypotheses, and prove root cause before implementation |

Install with `droid plugin install investigation@sagar-plugins`.

### [`practices`](./plugins/practices/) · productivity

Owns planning and the engineering policies used by the other workflows.

| Capability | Purpose |
| --- | --- |
| `spec` (public) | Scope and decompose non-trivial work |
| `planner` (droid) | Produce evidence-backed decisions, alternatives, units, sequencing, and open questions |
| `discovering-unknowns` | Find map-versus-territory gaps and carry the Deviations contract |
| `architecture-scan` | Rank ownership, boundary, state, failure, and test-seam opportunities |
| `grilling` | Stress-test one architecture-changing decision at a time |
| `tech-spec` | Define typed contracts, seams, adapters, call stacks, failures, and test slices |
| `tdd-workflow` | Enforce RED, GREEN, and refactor checkpoints |
| `coding-standards` | Route to standards for modules, boundaries, failures, async work, tests, observability, naming, and types |
| `verification-loop` | Discover and run build, type-check, lint, tests, and repository-specific gates |
| `agentic-engineering` | Set completion, delegation, model-routing, evaluation, and review policy |

Install with `droid plugin install practices@sagar-plugins`.

### [`build`](./plugins/build/) · productivity

Changes code and owns delivery.

| Capability | Purpose |
| --- | --- |
| `implement` (public) | Route approved units, new behavior, and mechanical edits to the right execution path |
| `ship` (public) | Commit, push, maintain the PR, watch CI, resolve threads, and report merge-ready |
| `implementer` (droid) | Apply an approved change set with minimal edits and targeted verification |
| `test-engineer` (droid) | Find risky coverage gaps or write behavior-pinning tests, including TDD RED |

Install with `droid plugin install build@sagar-plugins`.

### [`review`](./plugins/review/) · quality

Reviews diffs under explicit authority boundaries.

| Capability | Purpose |
| --- | --- |
| `review-pr` (public) | Select review depth and lenses, then report, fix, address comments, ship, or merge only as authorized |
| `change-review` (droid) | Trace correctness, contracts, state, async ordering, rollback, and failure behavior |
| `security` (droid) | Review with STRIDE and OWASP, and verify CVE claims against trusted sources |
| `review-worker` (droid) | Run deep review passes over a shared evidence document |

Install with `droid plugin install review@sagar-plugins`.

### [`synthesis`](./plugins/synthesis/) · productivity

Turns reviewed diffs into repository-facing prose.

| Droid | Purpose |
| --- | --- |
| `commit-message-writer` | Write a Conventional Commits message from staged changes |
| `pr-describer` | Write a PR title and body covering what, why, testing, breaking changes, and follow-ups |

Install with `droid plugin install synthesis@sagar-plugins`.

### [`meta`](./plugins/meta/) · productivity

Improves droid, skill, hook, and agentic-configuration prompts through measured iteration.

| Capability | Purpose |
| --- | --- |
| `audit-and-apply-loop` | Capture behavior, audit the prompt, apply a minimal change, and rerun the same case |
| `prompt-optimizer` (droid) | Audit one prompt or prompt pair without editing |
| `doc-generator` (droid) | Apply approved prompt and agentic-documentation changes |

Install with `droid plugin install meta@sagar-plugins`.

### [`guardrails`](./plugins/guardrails/) · quality

Adds deterministic controls around model-driven workflows.

| Hook | Purpose |
| --- | --- |
| Intent router | Routes planning, implementation, review, and shipping requests into the four public workflows |
| Push policy | Blocks direct default-branch pushes, literal `--force`/`-f`, `--no-verify`, and piped pushes without `pipefail` |
| Delivery ledger | Records session baselines and successful push state per repository |
| Completion gate | After a session push is recorded, requires no tracked changes or untracked files added since session start, matching local/remote/PR heads, green CI, resolved threads, and a fresh PR body |

Install with `droid plugin install guardrails@sagar-plugins`.

Total: 14 droids, 13 skills, 0 commands. Internal skills stay model-invoked, so the slash
menu remains limited to `spec`, `implement`, `review-pr`, and `ship`.

## Models

Each droid pins a model and reasoning effort suited to its job.

| Model | Role | Used by |
| --- | --- | --- |
| `gpt-5.6-sol` (xhigh) | Planning, repository investigation, root cause, and correctness review | `planner`, `deep-understanding`, `debugger`, `change-review`, `review-worker` |
| `gpt-5.6-terra` (high) | Implementation, testing, and precise config edits | `implementer`, `test-engineer`, `doc-generator` |
| `gpt-5.6-luna` (high/medium) | Triage and format-mechanical work | `quick-analysis`, `commit-message-writer` |
| `claude-opus-4-8` (xhigh/high) | Security, external research, prompt critique, and PR prose | `security`, `deep-research`, `prompt-optimizer`, `pr-describer` |

## Validation and versioning

Run the marketplace validator with:

```bash
node scripts/validate.mjs
```

It checks manifests, droid frontmatter, the four-skill public surface, README counts, and
parent-relative Markdown references inside plugins. CI also runs it with `--require-bumps`
against the PR base to enforce plugin and skill version changes.

Any change under `plugins/<name>/` bumps that plugin's semver version. A changed skill also
bumps its own `version` frontmatter. Droids version through their plugin manifest. CI
enforces these rules on pull requests.

## Repository layout

```text
sagar-plugins/
├── .factory-plugin/
│   └── marketplace.json      # marketplace catalog
├── .github/workflows/
│   └── validate.yml          # structural checks and policy tests
├── docs/
│   └── WORKFLOW.md           # detailed workflow contract
├── scripts/
│   └── validate.mjs          # marketplace validator
└── plugins/
    ├── investigation/        # 4 research and debugging droids
    ├── practices/            # planning droid + 9 policy skills
    ├── build/                # 2 execution droids + implement/ship
    ├── review/               # 3 review droids + review-pr
    ├── synthesis/            # commit and PR prose droids
    ├── meta/                 # prompt audit/apply droids + loop skill
    └── guardrails/           # deterministic workflow hooks
```
