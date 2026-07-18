# Golden Task 26: Prompt Optimizer Audits a Flawed Droid

Version: 1

## Target

`prompt-optimizer`.

## Setup

```bash
mkdir -p .factory/droids
cat > .factory/droids/log-helper.md <<'EOF'
---
name: log-helper
description: Helps with logs and stuff when needed.
model: gpt-5.6-luna
reasoningEffort: high
---

You are a logging assistant. Help the user with whatever they need around logging.

Always add as much logging as possible to every file you touch. Be conservative and change
as little as possible.

If something is unclear, make your best guess and proceed.
EOF
git add -A
git -c user.email=eval@local -c user.name=eval commit -qm "base: flawed log-helper droid"
git branch -m main
```

## Prompt

```text
Audit the droid prompt at .factory/droids/log-helper.md and recommend minimal-edit
improvements. Audit only; do not edit the file.
```

## Expected behavior

An audit that quotes the prompt's concrete defects: a vague, trigger-free description
("logs and stuff when needed"), a direct self-contradiction ("as much logging as possible"
versus "change as little as possible"), guess-and-proceed guidance that suppresses
clarification, and no output contract. Each finding comes with a minimal recommended edit,
prioritized. No files change.

## Must pass

- Flags the vague description as unroutable and proposes concrete activation wording.
- Quotes the contradiction between "as much logging as possible" and "change as little as
  possible" and proposes one resolved instruction.
- Flags "make your best guess and proceed" as suppressing necessary clarification and
  proposes decidable behavior.
- Flags the missing output contract (no `## Output` section) and proposes one.
- Presents findings in priority order with minimal, targeted edit recommendations
  (not a wholesale rewrite).
- Edits no files.

## Must not do

- Edit .factory/droids/log-helper.md or create replacement files.
- Rewrite the entire prompt as the recommendation.
- Give generic prompt-writing advice without quoting this prompt's text.
- Miss the self-contradiction.

## Score

- `pass`: all four defect classes found with quoted evidence and minimal prioritized
  recommendations, zero edits.
- `partial`: three of the four defect classes found with quoted evidence.
- `fail`: edits a file, misses the contradiction, or returns generic advice.
