# Golden Task 20: Conventional Commit Message from a Real Diff

Version: 1

## Target

`commit-message-writer`.

## Setup

```bash
mkdir -p src
cat > src/session.ts <<'EOF'
export function sessionUser(session: { user?: { id: string } }) {
  return session.user.id;
}
EOF
git add -A
git -c user.email=eval@local -c user.name=eval commit -qm "chore: base session helper"
git branch -m main
cat > src/session.ts <<'EOF'
export function sessionUser(session: { user?: { id: string } }) {
  if (!session.user) {
    return null;
  }
  return session.user.id;
}
EOF
cat > src/session.test.ts <<'EOF'
import { sessionUser } from './session';

test('returns null when the session has no user', () => {
  expect(sessionUser({})).toBeNull();
});
EOF
git add -A
git -c user.email=eval@local -c user.name=eval commit -qm "wip"
```

## Prompt

```text
The commit at HEAD carries the placeholder message "wip". Write the proper Conventional
Commits message for exactly that commit's diff (HEAD vs HEAD~1). Output the commit message
only; do not amend, commit, or push.
```

## Expected behavior

A single Conventional Commits message grounded in the actual diff: a `fix`-type subject for
the null-guard in `sessionUser`, optionally scoped, with body bullets covering the guard and
the added test, and nothing invented.

## Must pass

- Subject line matches Conventional Commits (`type(scope)?: description`), uses the `fix`
  type, and is 72 characters or fewer.
- Subject is imperative and describes the null-guard behavior change, not the session or
  process that produced it.
- Any body bullets reference only changes present in the diff (the guard in
  `src/session.ts`, the test in `src/session.test.ts`).
- Outputs the message only, with no surrounding commentary claiming actions were taken.

## Must not do

- Run `git commit`, `git commit --amend`, or `git push`.
- Invent ticket numbers, issue references, or co-authors.
- Use a type other than `fix` for a behavior-guard change (for example `feat` or `chore`).
- Mention files, functions, or motivations that do not appear in the diff.
- Claim tests were run.

## Score

- `pass`: well-formed `fix` message grounded entirely in the diff, message-only output.
- `partial`: correct subject but body includes one ungrounded or process-referencing line.
- `fail`: wrong type, malformed subject, invented references, or the commit was amended.
