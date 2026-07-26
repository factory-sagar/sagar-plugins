# Deep Review

Use deep review for a broad or high-consequence change as defined in `SKILL.md`, or when the
user explicitly asks for it. Authority remains in `SKILL.md`; depth never upgrades a read-only
request.

Spawn a second independent `change-review` context that has not seen the first reviewer's
findings. Give both reviewers the same scope, diff, relevant untracked-file list, and applicable
policy concerns. Reconcile the union of their findings before applying any correction.

For a landing request, follow the `SKILL.md` landing gate: explicit instruction, live green CI
for the current head, zero unresolved threads, and a final live-head equality check immediately
before merging.
