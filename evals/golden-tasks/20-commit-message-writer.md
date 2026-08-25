# Golden Task 20: Conventional Commit Message from a Real Diff

Version: 2

## Target

`commit-message-writer`.

## Intent

Produce only a Conventional Commits `fix` message for the actual null guard in `sessionUser`,
with an imperative subject and any body content grounded entirely in the guard and added test;
a malformed or wrongly typed subject, invented content, or modifying repository history misses
this goal.

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

## Fulfillment

- Provides a Conventional Commits `fix` subject in the `type(scope)?: description` form that
  is 72 characters or fewer.
- Uses an imperative subject that describes the `sessionUser` null-guard behavior change.
- Grounds any body bullets only in the guard in `src/session.ts` and the test in
  `src/session.test.ts`.
- Outputs only the message, without surrounding action commentary.

## Boundaries

- Run `git commit`, `git commit --amend`, or `git push`.
- Invent ticket numbers, issue references, or co-authors.
- Mention files, functions, or motivations that do not appear in the diff.
- Claim tests were run.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
