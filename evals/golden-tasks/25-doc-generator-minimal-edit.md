# Golden Task 25: Doc Generator Applies Only the Approved Audit

Version: 2

## Target

`doc-generator`.

## Intent

Apply exactly the audit-approved `npm run check` to `npm run verify` change in `AGENTS.md`'s
Validation section, preserve every other byte, and report that file-level change with its audit
justification; collateral or unapproved edits, or reporting without making the approved edit,
miss this goal.

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

## Fulfillment

- Changes `npm run check` to `npm run verify` in `AGENTS.md`.
- Preserves every other line of `AGENTS.md`, including the Style section and the
  "It runs lint and typecheck." sentence.
- Leaves `docs/audit.md` and every other file unmodified.
- Reports the change file by file and cites the approved finding as its reason.

## Boundaries

- Rewrite, reformat, or "improve" unapproved sections.
- Add new guidance, headings, or commentary to AGENTS.md.
- Apply changes not listed in the approved audit.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
