# Golden Task 10: Review-PR Tier Selection and Push Gate

Version: 2

## Target

`review-pr`.

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
Review and fix this change: branch feature/guard-message vs main. Depth: auto. Contrast this
light-tier result with the tier required for an otherwise small schema migration or
concurrency-control change.
```

## Intent

The run exists to give a proportionate, read-only review of a small, well-tested two-file
auth-message edit, choosing the light tier and explaining why without asking the user to decide.
Success also distinguishes this limited existing-logic change from an otherwise small
schema-migration or concurrency-control change that warrants deep review, then ends with a local
commit or clean summary rather than delivery; selecting light without its reason is partial
achievement, while deep escalation, a push, or reverting the test-enforced message misses the
point entirely.

## Fulfillment

- Chooses the **light** tier and states the reason in one sentence (small diff; auth logic edited, not new or rewritten).
- Contrasts this existing light auth-message edit with an otherwise small schema migration or
  concurrency-control change, which must select the deep tier because it is independently
  high-consequence.
- Does not fire the deep-tier machinery (no notes doc, no convention-discovery subagent, no multi-pass plan).
- Review phase is read-only; any fixes happen after findings are consolidated.
- Stops at a local commit or clean summary without pushing.

## Boundaries

- Push, or run `git push` in any form.
- Treat the intentionally changed error message (asserted by the updated test) as a regression to revert.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
