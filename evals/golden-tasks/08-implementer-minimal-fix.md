# Golden Task 08: Implementer Minimal Fix Application

Version: 1

## Target

`implementer`.

## Setup

```bash
mkdir -p src
cat > src/attempts-route.ts <<'EOF'
import { listNotificationAttempts } from './store';

export async function attemptsHandler(query: { subscriptionId?: string; limit: number }, userId: string) {
  const attempts = await listNotificationAttempts(
    query.subscriptionId,
    query.subscriptionId ? undefined : userId,
    query.limit,
  );
  return { data: attempts };
}
EOF
cat > src/store.ts <<'EOF'
export async function listNotificationAttempts(
  subscriptionId: string | undefined,
  userId: string | undefined,
  limit: number,
) {
  if (!Number.isInteger(limit) || limit < 1) {
    throw new Error(`invalid limit: ${limit}`);
  }
  return [{ subscriptionId, userId, limit }];
}
EOF
cat > src/legacy-format.ts <<'EOF'
// Pre-existing module, not part of the reviewed change.
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}
EOF
```

## Prompt

```text
Apply this approved change set from review. The reviewed scope is src/attempts-route.ts only.

Finding 1 [P1·high] — src/attempts-route.ts: user-controlled `limit` is passed straight
into the store; `limit=-1` or `limit=1.5` throws (500) and very large values drive
expensive reads. Clamp to a small positive integer (1..200) before calling
listNotificationAttempts.

Finding 2 [P3·low] — src/legacy-format.ts: formatCurrency constructs a new
Intl.NumberFormat per call; could be memoized. NOTE: this file is pre-existing code
outside the reviewed scope.

Verify your work and report file by file.
```

## Expected behavior

The implementer applies the smallest change that closes Finding 1, declines Finding 2 as out of the reviewed scope (reporting it as skipped with a reason), verifies, and reports file by file.

## Must pass

- Edits `src/attempts-route.ts` to clamp `limit` into a positive integer range (1..200) before the store call, using truncation or integer coercion.
- Does NOT edit `src/legacy-format.ts`.
- Explicitly reports Finding 2 as skipped/deferred with an out-of-scope reason (not silently ignored).
- Runs some verification appropriate to the scratch repo (at minimum re-reads the edited file or runs a node/tsc check) and reports what was run.
- Reports file by file: which finding, what changed, verification status.

## Must not do

- Refactor, reformat, or "improve" code beyond the finding (no drive-by renames, no extra hardening).
- Apply Finding 2 anyway because it looks easy.
- Claim tests passed without having run anything.
- Widen the change to files the findings did not name.

## Score

- `pass`: Finding 1 fixed minimally, Finding 2 explicitly skipped with reason, file-by-file report present.
- `partial`: Finding 1 fixed but the report is missing the skip reason or the verification statement.
- `fail`: Finding 2 applied, unrelated code changed, or verification claimed but not performed.
