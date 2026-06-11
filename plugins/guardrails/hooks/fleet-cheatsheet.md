## sagar-plugins fleet router

Delegation map for the installed sagar-plugins fleet. Prefer delegating matching work to these droids and skills instead of doing it inline.

Droids (invoke via Task tool):
- quick-analysis: fast repo triage; first stop in an unfamiliar repo
- deep-understanding: thorough, evidence-based investigation of a system or focused question
- deep-research: external/web questions answered with cited evidence
- debugger: failing test, stack trace, regression, or flaky behavior; finds root cause, never patches
- implementer: applies an approved change set (review findings, spec unit, fix list)
- test-engineer: ranks riskiest untested behavior and writes the missing tests (incl. TDD RED)
- change-review: strict pre-merge review of a diff, commit, or branch
- security: security review of diffs or explicitly scoped files
- pr-describer: PR title and body from a diff
- commit-message-writer: Conventional Commits message from staged changes
- prompt-optimizer then doc-generator: audit then apply edits to droid/skill prompts and AGENTS.md

Skills:
- spec: fuzzy request to concrete spec plus droid-tagged work units
- tdd-workflow: RED-GREEN-REFACTOR for new behavior and bug fixes
- verification-loop: build/typecheck/lint/test gate before review or PR
- coding-standards: conventions bar and code-smell review checklist
- agentic-engineering: delegation and model-routing operating principles
- demo-prep: verify a demo app end to end before showing it
- audit-and-apply-loop: evolve droid and skill prompts safely

Standard loop: spec, then per unit investigate (quick-analysis / deep-understanding / debugger), implement (tdd-workflow), verify (verification-loop), review (change-review + security), then synthesize (commit-message-writer + pr-describer).
