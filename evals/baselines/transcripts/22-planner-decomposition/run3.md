# Plan: Soft-Delete and Restore Notes

## Summary

Replace physical note removal with an internal deletion marker, exclude deleted notes from normal listings, and add `POST /notes/:id/restore`. Preserve existing thin-route and ownership conventions.

## Decisions

- **D1: Keep deleted notes in the existing `Map` with a system-owned, optional `deletedAt` timestamp.** Deletion sets it once, listing excludes marked notes, and restoration removes it. Evidence: `src/store/notes.js:1-15`. Rejected: hard deletion, because restoration becomes impossible / separate tombstone collection, because it splits record state / boolean marker, because it loses deletion-time information.
- **D2: Keep lifecycle behavior and ownership enforcement in the store.** Add `restoreNote(userId, id)` beside `deleteNote`; routes only pass authenticated user and path ID. Evidence: `docs/conventions.md:2-3`, `src/routes/notes.js:3-9`. Rejected: route-layer ownership or filtering, because it violates documented boundaries / direct route access to the private `Map`, because it leaks storage concerns / a new deleted-notes endpoint, because it is outside the requested scope.
- **D3: Make restoration idempotent and non-disclosing, returning `204`.** Missing, active, or foreign-owned notes remain silent no-ops, matching current deletion semantics. Evidence: `src/store/notes.js:13-15`, `src/routes/notes.js:6-8`. Rejected: `200` with the note, because it introduces a new response contract / `403` or `404`, because it changes existing non-disclosure behavior / `409` for active notes, because it prevents safe retries.

## Goal / Non-goals

- **Goal:** Preserve owned deleted notes for restoration while removing them from `GET /notes`.
- **Non-goals:** Trash listing, permanent purge, retention policy, database migration, cross-process persistence, or unrelated note schema changes.

## Acceptance Criteria

- Newly created notes appear in their owner’s listing.
- `DELETE /notes/:id` returns `204`, preserves the record, and hides it from listings.
- `POST /notes/:id/restore` returns `204` and makes the same ID and content visible again.
- Delete and restore remain restricted to the owning user.
- Missing, foreign-owned, already-deleted, and already-active operations are safe and idempotent.
- Client input cannot create a note already marked as deleted.
- Repeated delete, restore, and delete-after-restore transitions behave consistently.
- Store and route regression tests pass through the repository’s available runtime.

## Territory

| Constraint / convention / gate | Evidence | Bearing on the plan |
| --- | --- | --- |
| Notes use process-local `Map` storage | `src/store/notes.js:1` | Soft deletion must retain the record in this map. |
| Listing currently filters only by ownership | `src/store/notes.js:3-5` | Add active-state filtering without weakening user isolation. |
| Creation spreads client data into records | `src/store/notes.js:7-10` | `deletedAt` must be reserved and cleared from client input. |
| Deletion currently checks ownership then removes the record | `src/store/notes.js:13-15` | Replace physical removal with an owned state transition. |
| Routes delegate directly to store functions | `src/routes/notes.js:1-9` | Restore follows the same registration and delegation shape. |
| Behavior belongs in store modules | `docs/conventions.md:2-3` | Route handlers should not inspect or mutate deletion state. |
| No tracked test, package, CI, lint, or build configuration was found | Repository inventory recorded below | Add dependency-free Node tests and run them directly rather than inventing broader tooling. |

## Units

### U1: Implement the note lifecycle seam [executor: `tdd-workflow`] [risk: high]

- **Scope:** Test and implement soft deletion, listing exclusion, restoration, ownership, and idempotency in the store.
- **Files:** `src/store/notes.js`, `test/store/notes.test.js` (new)
- **Acceptance:** Deleting retains the note but hides it; restoring resurfaces the same record; foreign users cannot change state; repeated transitions are safe; client-provided deletion metadata is ignored.
- **Depends on:** None
- **Deviations contract:** Minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

### U2: Expose the restore route [executor: `tdd-workflow`] [risk: low]

- **Scope:** Register `POST /notes/:id/restore`, delegate to `restoreNote`, and return `204`.
- **Files:** `src/routes/notes.js`, `test/routes/notes.test.js` (new)
- **Acceptance:** A route-level test verifies method, path, authenticated user forwarding, path-ID forwarding, and `204` completion; existing routes remain unchanged.
- **Depends on:** U1
- **Deviations contract:** Minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

### U3: Run the repository validation gate [executor: `implementer`] [risk: low]

- **Scope:** Execute all new tests without adding unrelated dependencies or build tooling.
- **Files:** No production changes
- **Acceptance:** `node --experimental-default-type=module --test test/store/notes.test.js test/routes/notes.test.js` passes.
- **Depends on:** U1, U2
- **Deviations contract:** Minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

## Sequencing

- **Wave 1:** U1
- **Wave 2:** U2
- **Wave 3:** U3
- **First visible result:** U1 demonstrates that a deleted note disappears and subsequently returns with its original ID and content.

## Risks & Rollback

- Client-controlled `deletedAt` could hide new notes → reserve and remove that field during creation.
- Ownership regressions could expose another user’s note → test both delete and restore across distinct users.
- Soft-deleted records accumulate indefinitely → accept as the requested retention behavior; add purge only through a separately scoped feature.
- Rollback → remove the restore route and tests, then restore `notes.delete(id)` in `deleteNote`.

## Open Questions

- **Q1: Must restoration survive process restarts?** Recommended: no, retain the existing process-local storage boundary. If taken: notes survive deletion but not application restart.
- **Q2: Is permanent deletion or retention expiry required?** Recommended: no, preserve deleted records indefinitely within the current store lifetime. If taken: no purge API or cleanup scheduler is added.
- **Q3: Should deletion metadata be externally visible?** Recommended: no, keep `deletedAt` internal and remove it on restore. If taken: active note response shapes remain unchanged.

## Evidence Log

- Read `docs/conventions.md`, `src/store/notes.js`, and `src/routes/notes.js`.
- Searched source and documentation for route patterns, ownership checks, restore behavior, TODOs, and test gates.
- Inspected tracked-tree inventory with `git ls-tree -r --name-only HEAD`.
- Inspected target-file history with `git log -p -- src/store/notes.js src/routes/notes.js`.
- Checked branches, tags, and Git notes; no prior soft-delete implementation or rejected approach exists.
