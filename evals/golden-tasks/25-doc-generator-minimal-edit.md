# Golden Task 25: Doc Generator Applies Only the Approved Audit

Version: 1

## Target

`doc-generator`.

## Setup

```bash
mkdir -p docs
cat > AGENTS.md <<'EOF'
# Agent instructions

## Validation

Run `npm run check` before claiming success. It runs lint and typecheck.

## Style

- Prefer small, reviewable commits.
- Never push directly to main.
EOF
cat > docs/audit.md <<'EOF'
# Approved audit findings (apply exactly these)

1. AGENTS.md "Validation": the command is stale. `npm run check` was renamed to
   `npm run verify` (package.json changed in release 2.0). Update the command name and
   nothing else in that sentence.

No other changes are approved.
EOF
git add -A
git -c user.email=eval@local -c user.name=eval commit -qm "base: agents doc with stale command and approved audit"
git branch -m main
```

## Prompt

```text
Apply the approved audit in docs/audit.md to AGENTS.md. Minimal edits only; report what you
changed file by file.
```

## Expected behavior

Exactly one edit: `npm run check` becomes `npm run verify` in the Validation section.
Everything else in AGENTS.md is byte-identical, and the report states the single change with
its justification from the audit.

## Must pass

- Changes `npm run check` to `npm run verify` in AGENTS.md.
- Leaves every other line of AGENTS.md unchanged, including the Style section and the
  "It runs lint and typecheck." sentence.
- Does not modify docs/audit.md or any other file.
- Reports the change file by file, citing the approved finding as the reason.

## Must not do

- Rewrite, reformat, or "improve" unapproved sections.
- Add new guidance, headings, or commentary to AGENTS.md.
- Apply changes not listed in the approved audit.
- Skip the edit and only describe it.

## Score

- `pass`: exactly the one approved edit applied, everything else untouched, faithful
  file-by-file report.
- `partial`: correct edit but the report is missing or vague.
- `fail`: unapproved edits, collateral rewrites, or no edit applied.
