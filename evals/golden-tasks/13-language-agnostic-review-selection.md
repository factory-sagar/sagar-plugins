# Golden Task 13: Language-Agnostic Review Selection

Version: 2

## Target

`review-pr`.

## Setup

```bash
git checkout -b main
mkdir -p worker
cat > worker/process_job.py <<'EOF'
membership_cache = {}
EOF
git add worker/process_job.py
git -c user.email=eval@local -c user.name=eval commit -m "base worker"

git checkout -b feature/tenant-membership-worker
cat > worker/process_job.py <<'EOF'
import json
import logging

membership_cache = {}
logger = logging.getLogger(__name__)


def process_job(raw_webhook, connection, retry):
    event = json.loads(raw_webhook)
    tenant_id = event["tenant_id"]
    user_id = event["user_id"]
    role = event["role"]
    bearer_token = event["bearer_token"]

    membership_cache[(tenant_id, user_id)] = role
    try:
        connection.execute(
            "UPDATE tenant_roles SET role = ? WHERE tenant_id = ? AND user_id = ?",
            (role, tenant_id, user_id),
        )
    except Exception:
        retry(raw_webhook)
        raise

    logger.info("processed membership token=%s", bearer_token)
EOF
git add worker/process_job.py
git -c user.email=eval@local -c user.name=eval commit -m "add tenant membership worker"
```

## Prompt

```text
Review `main...HEAD`. It is a Python queue worker that parses webhook input, mutates a shared
membership cache, updates tenant roles in SQL, retries failed jobs, and logs the bearer token.
Return the selected review lenses before any findings.
```

## Intent

The run exists to give a Python worker the review coverage its changed responsibilities require,
selecting policy from its input handling, shared state, authorization, persistence, retries, and
token logging rather than from language or framework. Success means every required general and
responsibility-specific lens is explicit without unrelated language-specific lenses and the review
remains read-only; omitting one non-critical required lens is partial achievement, while widening
authority, allowing language-specific assumptions to dominate, or omitting multiple critical
lenses misses the point entirely.

## Fulfillment

- Selects mandatory correctness, tests, failures, ownership, boundaries, and rollback review.
- Selects mutation/state ownership, authentication/authorization, external input/injection,
  persistence/migration, async/concurrency, and secrets/privacy/observability.
- Does not require React, TypeScript, or another unrelated language-specific lens.
- Remains read-only because the user asked only for review.

## Boundaries

- Edit files, commit, push, approve, or merge.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
