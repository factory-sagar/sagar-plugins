# Review-PR Notes Format

This file defines the shared notes-doc format used by `review-pr` deep mode,
`review-worker.md`, the Discovery subagent, and the Review subagent. The notes doc is
the source of truth for every pattern-check, codepath note, finding, and filter annotation.

## Notes doc skeleton

The manager MUST create stable notes and initial-context paths outside the repo before spawning
subagents:

```bash
mkdir -p /tmp/factory-review-pr-notes
NOTES_PATH=/tmp/factory-review-pr-notes/$(date +%s)-$(openssl rand -hex 4).md
CONTEXT_PATH="${NOTES_PATH%.md}-context.md"
cat > "$NOTES_PATH" <<'EOF'
# Review-PR Notes for <PR URL / branch / scope>

## Review Context
<!-- Manager appends the completed Initial Review context here after concurrent startup. -->

## Pattern Checks
<!-- Discovery appends one entry per pattern-check here. Review fills verdicts. Manager annotates filters. -->

## Codepath Notes
<!-- Passes 1-4 model-driven findings live here, one entry per codepath. -->

## Findings
<!-- Every finding that may become a fix lives here, one Markdown block per finding. -->

## Filter Status
<!-- Every final filter appends one completion entry here before returning. -->
EOF
cat > "$CONTEXT_PATH" <<'EOF'
# Initial Review Context
<!-- Initial Review writes intent, scope, constraints, and linked-context gaps here. -->
EOF
```

Discovery is the only concurrent startup subagent that writes `NOTES_PATH`. Initial Review writes
only `CONTEXT_PATH`; it must not read or write `NOTES_PATH` during that concurrent startup. After
both return, the manager reads `CONTEXT_PATH`, appends its completed content under `## Review
Context` in `NOTES_PATH`, then audits it before any later Review pass. All later Review passes and
the final filter use `NOTES_PATH`. This serial handoff prevents concurrent writes to one file.

## Pattern check entry format

Discovery appends each pattern-check to `## Pattern Checks` with this exact Markdown format:

```md
### [<category>] <name>
- source_doc: <repo-relative path or coding-standards topic>
- description: <1-3 sentence rule>
- **Verdict: pending**
```

The Review subagent replaces `- **Verdict: pending**` with one or more final verdict lines:

```md
- **Verdict: finding** — see finding "<title>" in `## Findings`
- **Verdict: verified-clean** — <body naming the specific file:line locations considered, with concrete evidence>
```

If a pattern is violated in multiple places, replace the pending placeholder with multiple
`finding` verdict lines — one per site.

## Codepath note format

For Passes 1-4, the Review subagent appends one entry per considered codepath to `## Codepath Notes`:

```md
### [Pass N] <short codepath name>
- codepath: <file:line or feature area>
- **Verdict: finding** — see finding "<title>" in `## Findings`
```

or:

```md
### [Pass N] <short codepath name>
- codepath: <file:line or feature area>
- **Verdict: verified-clean** — <body explaining why the codepath is healthy on this pass's specific concern, with file:line citation>
```

## Finding Markdown format

Whenever the Review subagent writes a finding to the notes doc, and whenever the manager carries
findings forward to the fix phase, use this exact Markdown block:

```text
### [Blocking|Non-Blocking|Nit]: <title>
<description>
<filepath>(#<line>|#<start>-<end>)?
Category: <pass name without numeric index>
```

Rules:

- Use exactly one of `Blocking`, `Non-Blocking`, or `Nit`.
- Keep `<title>` imperative and specific.
- Write `<description>` as clear, readable prose that explains the concrete issue, the
  user/system impact, and the requested change.
- Include guideline references whenever possible (a `coding-standards` topic doc, the target
  repo's `docs/*` or an `AGENTS.md`) and cite sibling-file precedent when that is the source of
  the convention.
- Put the primary citation on its own line as `path#42` or `path#42-57`. If the finding genuinely
  has no precise line, use just `path`.
- `Category:` is the pass name without the numeric index, such as `Functional Correctness`,
  `User and System Impact`, `Completeness`, `Code Organization`, `Style guide`, `Security`, or a
  dynamic category like `Error & Logging`. Do not write `Pass 4` in the category.

Example:

```md
### [Non-Blocking]: Extract the repeated status shape
The new `status` object shape is repeated in both the API response and the CLI renderer. The
type-contracts standard asks repeated structural shapes to be promoted to a named type, so
extract a shared `DaemonStatus` type and reuse it in both places instead of letting the two
copies drift.
src/daemon/status.ts#42-58
Category: Code Organization
```

## Filter annotation format

The final filter pass does not rewrite findings. For every invalid finding, append this line
directly under that finding block in `## Findings`:

```md
**Filter: <reason code>** — <justification>
```

Valid reason codes are defined in `review-worker.md` under the final filter prompt.

## Filter status format

Every final filter appends one completion entry to `## Filter Status`, including when it removes
zero findings:

```md
### Final Filter
- Filtered: <count>
- Kept: <count>
- Status: complete
- Blockers: none
- Evidence Coverage: all finding blocks filtered or kept
```

## Findings carried to the fix phase

After the final filter, the manager carries every UNFILTERED finding block from `## Findings`
into Step 4 of the skill (triage) and Step 5 (fix). The order of emission is Blocking, then
Non-Blocking, then Nit. Each finding must remain uniquely referrable so the fix summary can map
fixes back to findings.

## Citation requirement

- Model-driven findings (Passes 1-4) cite `file:line` evidence — the
  specific code, contract, or call site that demonstrates the issue.
- Convention findings (Passes 5+) cite either a documented convention or a sibling-file pattern.

Findings without any citable source are weaker — move them to Nit or drop them.
