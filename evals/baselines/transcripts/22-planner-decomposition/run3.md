# Plan: Soft-Delete and Restore Notes

## Summary

Replace physical note removal with an internal tombstone, exclude deleted notes from normal listings, and add `POST /notes/:id/restore`. Preserve the current in-memory storage and opaque ownership semantics.

## Decisions

- **D1: Store active and deleted notes in the existing `Map` using an internal record envelope.** Each entry becomes `{ note, deleted }`, preserving the public note shape while retaining deleted records. Evidence: `src/store/notes.js:1`, `src/store/notes.js:7-10`, `src/store/notes.js:13-15`. Rejected: mutating public notes with `deletedAt`, because lifecycle metadata could leak through returned object references; separate active/archive maps, because split ownership complicates lookup and identifier allocation; durable database storage, because the entire current store is intentionally in memory.
- **D2: Keep filtering, ownership checks, deletion, and restoration in the store layer.** Routes should only forward the authenticated user and note ID. Evidence: `docs/conventions.md:2-3`, `src/routes/notes.js:4-8`, `src/store/notes.js:13-15`. Rejected: filtering or restoring in route handlers, because it violates the thin-route convention; exposing deleted records to routes, because it spreads lifecycle rules across layers.
- **D3: Make restore an idempotent, opaque command returning `204 No Content`.** Missing notes, notes owned by another user, and already-active notes remain no-ops, matching current deletion behavior and avoiding resource enumeration. Evidence: `src/routes/notes.js:6-9`, `src/store/notes.js:13-15`. Rejected: `200` with the restored note, because it introduces a new response shape unnecessarily; `404`/`409`, because the repository has no error contract and distinguishable responses could expose note existence.

## Goal / Non-goals

- **Goal:** Soft-delete notes, hide them from `GET /notes`, and restore owned notes through `POST /notes/:id/restore`.
- **Settled constraints:** Deleted records must remain in storage; the restore path is exactly `/notes/:id/restore`; normal listings must exclude deleted notes.
- **Non-goals:** Durable storage across process restarts, retention or purge policies, listing deleted notes, changing authentication, exposing deletion metadata, or adding unrelated note APIs.

## Acceptance Criteria

- `DELETE /notes/:id` retains the owned note in the store and returns `204`.
- Deleted notes do not appear in `GET /notes`.
- `POST /notes/:id/restore` returns `204` and makes an owned deleted note visible again.
- Missing, foreign-owned, already-deleted, and already-active transitions remain safe and idempotent.
- One user cannot delete or restore another user’s note.
- Public note responses do not expose the internal deletion marker.
- Existing create and active-list behavior remains unchanged.
- Store and route tests pass through a repository-defined `npm test` command.

## Territory

| Constraint / convention / gate | Evidence | Bearing on the plan |
| --- | --- | --- |
| Notes currently live in one in-memory `Map`. | `src/store/notes.js:1` | Soft deletion should retain entries in this store rather than introduce persistence infrastructure. |
| Listing currently filters only by owner. | `src/store/notes.js:3-4` | Listing must additionally exclude tombstoned records while preserving ownership filtering. |
| IDs derive from the store size. | `src/store/notes.js:7-10` | Retaining deleted entries prevents ID reuse under the existing allocation scheme. |
| Deletion currently checks ownership and physically removes the entry. | `src/store/notes.js:13-15` | Replace only the removal operation with a state transition and mirror its ownership behavior in restoration. |
| Routes forward authenticated identity into store operations. | `src/routes/notes.js:4-8` | The restore route should call `restoreNote(req.user.id, req.params.id)`. |
| Route handlers must remain thin. | `docs/conventions.md:2` | Lifecycle rules and filtering belong in `src/store/notes.js`. |
| Destructive operations require store-layer ownership checks. | `docs/conventions.md:3` | Delete must preserve its ownership check; restore should use the same protection. |
| Source files use ES modules, but no tracked test runner or package manifest exists. | `src/routes/notes.js:1`, `src/store/notes.js:3` | Add a minimal ES-module package manifest and zero-dependency Node tests. |

## Units

### U1: Implement and test the store lifecycle [executor: `tdd-workflow`] [risk: high]

- **Scope:** Establish the zero-dependency test harness, then replace hard deletion with an internal tombstone and add an ownership-aware `restoreNote` operation.
- **Files:** `package.json`, `src/store/notes.js`, `test/notes-store.test.js`
- **Acceptance:**
  - `package.json` declares ES-module behavior and an `npm test` script using Node’s built-in test runner.
  - Store tests cover create/list, deletion retention, exclusion from listing, restoration, repeated transitions, missing IDs, and cross-user attempts.
  - The internal record envelope never appears in returned notes.
  - `deleteNote` and `restoreNote` mutate only records owned by the supplied user.
  - No production-only reset or test hook is introduced.
  - `node --test test/notes-store.test.js` passes.
- **Depends on:** None.
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

### U2: Add and test the restore endpoint [executor: `tdd-workflow`] [risk: high]

- **Scope:** Register `POST /notes/:id/restore` as a thin command handler backed by `restoreNote`.
- **Files:** `src/routes/notes.js`, `test/notes-routes.test.js`
- **Acceptance:**
  - The route passes `req.user.id` and `req.params.id` to `restoreNote`.
  - Successful, repeated, missing, and unauthorized restore attempts return `204` without a response body.
  - A delete followed by restore causes the note to disappear and reappear through the listing route.
  - Existing `GET /notes`, `POST /notes`, and `DELETE /notes/:id` route behavior remains covered.
  - Route tests use a lightweight fake app/response seam rather than introducing an unproven web-framework dependency.
  - The complete `npm test` suite passes.
- **Depends on:** U1.
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

## Sequencing

- **Wave 1:** U1, establish tested lifecycle semantics in the owning store.
- **Wave 2:** U2, expose the tested restore operation through HTTP and run the complete suite.
- **First visible result:** After U1, a deleted note can be restored through the store API and remains hidden while deleted.

## Risks & Rollback

- **Internal record-shape regression:** Centralize envelope conversion inside the store and test public return shapes. Roll back by restoring direct note values and hard deletion.
- **Unauthorized note probing:** Preserve opaque no-op behavior and uniform `204` responses.
- **Unbounded memory growth:** Accept within the existing in-memory model; add retention only through a separately approved policy.
- **Route/store contract drift:** Cover the delete-list-restore-list sequence through the registered route handlers.

## Open Questions

- **Q1: Should soft-deleted notes eventually expire?** Recommended: no expiration in this feature. If taken, notes remain restorable for the lifetime of the current process and retention can be designed separately.
- **Q2: Should deleted notes become queryable through an administrative API?** Recommended: no. If taken, this change remains limited to normal listing and restoration without expanding authorization scope.

## Evidence Log

- Read `docs/conventions.md`, `src/store/notes.js`, and `src/routes/notes.js`.
- Searched `src/**` and `docs/**` for deletion, restoration, ownership, TODOs, and prior soft-delete work; no prior restore implementation or deferred design was found.
- Inspected repository history for `src` and `docs`; only base commit `e0bde51` exists.
- Inspected the committed tree; it contains only the conventions document and the two notes modules.
