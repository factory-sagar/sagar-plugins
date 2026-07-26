# Plan: Soft-delete and restore notes

## Summary

Replace destructive note removal with an ownership-checked tombstone lifecycle. Active listings exclude deleted notes, while `POST /notes/:id/restore` revives the original stored note.

## Decisions

- **D1 - Keep deleted notes in the existing `Map`, with deletion state stored separately.** Evidence: `src/store/notes.js:1-15`. Rejected: remove entries, which makes restore impossible / maintain a second archive map, which introduces synchronization and ownership duplication.
- **D2 - Keep lifecycle and ownership policy in the store.** Evidence: `docs/conventions.md:2-3`, `src/routes/notes.js:4-9`. Rejected: enforce ownership in routes, which violates the thin-route convention / expose raw note lookup to routes, which leaks storage policy.
- **D3 - Make delete and restore idempotent, preserving the current `204` command response.** Evidence: `src/routes/notes.js:6-9`; the current store silently ignores missing or foreign-owned notes at `src/store/notes.js:13-15`. Rejected: return restored note bodies, which creates a new response convention / surface existence or ownership differences, which could disclose another user's note.
- **D4 - Add a minimal dependency-free behavior-test harness.** Evidence: the complete tracked tree contains only `docs/conventions.md`, `src/routes/notes.js`, and `src/store/notes.js`; no package, test, or CI configuration exists. Rejected: introduce a third-party runner, which is unnecessary for this small ESM module / leave behavior unverified, which would not protect the new lifecycle invariants.

## Goal / Non-goals

- **Goal:** Deleting a note hides it without destroying it, and its owner can restore it through `POST /notes/:id/restore`.
- **Non-goals:** Permanent purge, listing deleted notes, retention expiry, durable persistence across process restarts, or a broad authentication/error-handling refactor.

## Acceptance Criteria

- Deleting an owned active note makes it disappear from `GET /notes`.
- The deleted note remains stored with its original ID and content.
- `POST /notes/:id/restore` restores an owned deleted note and returns `204`.
- A restored note reappears in `GET /notes` exactly once.
- Delete and restore are idempotent.
- One user cannot delete or restore another user's note.
- Active note creation and listing behavior remains unchanged.

## Territory

| Constraint / convention / gate | Evidence | Bearing on the plan |
| --- | --- | --- |
| Notes use one process-local `Map` | `src/store/notes.js:1` | Soft deletion must retain entries in this collection; restart durability remains out of scope. |
| Listings currently filter only by owner | `src/store/notes.js:3-5` | Add the active/deleted predicate alongside the ownership predicate. |
| Creation derives IDs from map size | `src/store/notes.js:7-10` | Retaining entries avoids reusing IDs caused by shrinking the map. |
| Delete currently performs physical removal after an ownership check | `src/store/notes.js:13-15` | Replace removal with an ownership-checked lifecycle transition. |
| HTTP handlers delegate behavior to the store | `src/routes/notes.js:4-9` | Restore should be a thin route calling `restoreNote(userId, id)`. |
| Destructive behavior belongs in the store | `docs/conventions.md:1-3` | Both delete and restore authorization stay below the route layer. |
| No runnable validation gate is checked in | whole-repository tracked-file scan | The implementation needs a minimal test command before behavioral work can be verified. |

## Units

### U1 - Establish the notes behavior-test seam [executor: test-engineer] [risk: low]

- **Scope:** Add a dependency-free ESM test harness and fixtures that exercise exported store functions without private-helper access.
- **Files:** `package.json`, `src/store/notes.test.js`, optionally a store reset seam if test isolation cannot be achieved through public behavior.
- **Acceptance:** The canonical test command runs; tests pin current create/list ownership behavior and initially fail for soft-delete and restore expectations.
- **Depends on:** none
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

### U2 - Implement store-owned soft-delete lifecycle [executor: tdd-workflow] [risk: high]

- **Scope:** Replace physical removal with tombstone state, exclude tombstoned notes from `listNotes`, and export an ownership-checked, idempotent `restoreNote`.
- **Files:** `src/store/notes.js`, `src/store/notes.test.js`
- **Acceptance:** Tests prove delete hides but retains a note, restore revives the original record, repeated transitions are no-ops, and cross-user transitions cannot change visibility.
- **Depends on:** U1
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

### U3 - Expose the restore HTTP endpoint [executor: tdd-workflow] [risk: low]

- **Scope:** Import `restoreNote` and register `POST /notes/:id/restore` as thin framework glue.
- **Files:** `src/routes/notes.js`, `src/routes/notes.test.js`
- **Acceptance:** Route-level behavior proves the authenticated user ID and route parameter reach the store contract, and the endpoint returns `204`; existing routes retain their responses.
- **Depends on:** U2
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

### U4 - Run the repository verification gate [executor: implementer] [risk: low]

- **Scope:** Run the canonical tests and inspect the final diff for accidental API or scope changes.
- **Files:** all changed files
- **Acceptance:** All tests pass, no deleted-note listing regression remains, and only the planned store, route, and test-harness files changed.
- **Depends on:** U2, U3
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

## Sequencing

- **Wave 1:** U1
- **Wave 2:** U2
- **Wave 3:** U3
- **Wave 4:** U4
- **First visible result:** U2, where deleting and restoring a note works through the store interface.

## Risks & Rollback

- **Accidental data exposure:** A foreign user could restore another user's note. Mitigate by keeping lookup and ownership checks inside `restoreNote`.
- **State leakage:** If tombstone metadata is returned publicly, response shapes could change. Keep lifecycle state internal to the store.
- **Test isolation:** Module-level storage persists across tests. Use isolated module instances or the smallest explicit test seam.
- **Rollback:** Revert the restore route and store lifecycle together; do not leave an endpoint whose backing transition has been removed.

## Open Questions

- **Q1:** Should deleted-note metadata be public? **Recommended:** No, keep tombstone state internal. **If taken:** existing create/list response shapes remain unchanged.
- **Q2:** Should restoring an active, missing, or foreign-owned note return `204`? **Recommended:** Yes. **If taken:** commands remain idempotent and do not disclose note existence.
- **Q3:** Should deletion record a timestamp? **Recommended:** No for this scope. **If taken:** the model remains minimal; retention and purge can add timestamps later.

## Evidence Log

- Read `docs/conventions.md`.
- Read `src/store/notes.js` and `src/routes/notes.js`.
- Searched all source for note, delete, restore, ownership, and response patterns.
- Inspected the full tracked tree for test, package, and CI configuration.
- Inspected notes history; only commit `6fa1a69` exists, with no prior restore attempt, revert, or explanatory TODO.
