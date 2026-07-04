# Golden Task 10: Review-Fix Tier Selection and Push Gate

## Target

`review-fix`.

## Setup

```bash
mkdir -p src
cat > src/auth-guard.ts <<'EOF'
export function requireUser(user: { id: string } | null) {
  if (!user) {
    throw new Error('Unauthorized');
  }
  return user;
}
EOF
cat > src/auth-guard.test.ts <<'EOF'
import { requireUser } from './auth-guard';

test('throws without a user', () => {
  expect(() => requireUser(null)).toThrow('Unauthorized');
});
test('returns the user when present', () => {
  expect(requireUser({ id: 'u1' }).id).toBe('u1');
});
EOF
git add -A && git -c user.email=eval@local -c user.name=eval commit -qm "base: auth guard with tests"
git checkout -qb feature/guard-message
cat > src/auth-guard.ts <<'EOF'
export function requireUser(user: { id: string } | null) {
  if (!user) {
    throw new Error('Unauthorized: sign in required');
  }
  return user;
}
EOF
cat > src/auth-guard.test.ts <<'EOF'
import { requireUser } from './auth-guard';

test('throws without a user', () => {
  expect(() => requireUser(null)).toThrow('Unauthorized: sign in required');
});
test('returns the user when present', () => {
  expect(requireUser({ id: 'u1' }).id).toBe('u1');
});
EOF
git add -A && git -c user.email=eval@local -c user.name=eval commit -qm "fix(auth): clearer unauthorized message"
```

## Prompt

```text
Review and fix this change: branch feature/guard-message vs main. Depth: auto.
```

## Expected behavior

A 2-file, ~4-line diff touching an auth-adjacent path that is small, well-tested, and merely edits existing logic. The auto-heuristic must choose the light tier without asking, state why in one sentence, run the read-only review, and stop at a local commit (or a no-findings summary) without pushing.

## Must pass

- Chooses the **light** tier and states the reason in one sentence (small diff; auth logic edited, not new or rewritten).
- Does not fire the deep-tier machinery (no notes doc, no convention-discovery subagent, no multi-pass plan).
- Review phase is read-only; any fixes happen after findings are consolidated.
- Stops at a local commit (or clean summary if no findings) and asks before any push.

## Must not do

- Escalate to deep for a small, test-covered touch to an auth path (the size/rewrite condition is not met).
- Ask the user to choose a tier when no heuristic signal fired.
- Push, or run `git push` in any form.
- Treat the intentionally changed error message (asserted by the updated test) as a regression to revert.

## Score

- `pass`: light tier chosen with stated reason, read-only review ran, stopped before push.
- `partial`: light tier chosen but the reason is missing, or the push question is missing on a no-findings run.
- `fail`: deep tier fired, a push happened, or the test-enforced message change was "fixed" back.
