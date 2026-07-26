# Plan: Soft-Delete and Restore Notes

## Summary

Replace physical note removal with an ownership-checked lifecycle state. Deleted notes remain stored, disappear from normal listings, and can be restored through `POST /notes/:id/restore`.

## Decisions

- **D1: Keep active and deleted notes in the existing `Map` using an internal `{ note, deleted }` envelope.** This preserves public note shapes while retaining restorable records. Evidence: `src/store/notes.js:1`, `src/store/notes.js:7-10`, `src/store/notes.js:13-15`. Rejected: adding `deleted` directly to public notes, because metadata could leak through API responses / using a separate archive map, because synchronization and ownership logic would be duplicated.
- **D2: Own filtering, authorization, and lifecycle transitions in the store.** Routes only forward `userId` and `id`. Evidence: `docs/conventions.md:2-3`, `src/routes/notes.js:4-9`, `src/store/notes.js:13-15`. Rejected: route-layer ownership checks, because they violate the documented boundary / exposing raw deleted records to routes, because it spreads lifecycle policy across layers.
- **D3: Make delete and restore idempotent opaque commands returning `204`.** Missing, foreign-owned, already-deleted, and already-active records remain no-ops. Evidence: `src/routes/notes.js:6-9`, `src/store/notes.js:13-15`. Rejected: `200` with a note body, because it creates an unnecessary response contract / distinguishable `403`, `404`, or `409` responses, because they could disclose note existence.
- **D4: Establish dependency-free behavioral tests before implementation.** Existing modules use ESM (`src/routes/notes.js:1`, `src/store/notes.js:3`), while the tracked repository has no test configuration. Use Node’s built-in test runner. Rejected: adding a third-party framework, because this scope does not justify another dependency / implementing without regression tests, because lifecycle and ownership failures risk data loss or exposure.

## Goal / Non-goals

- **Goal:** An owner can delete, hide, and later restore a note without losing its ID or content.
- **Settled constraints:** The endpoint is `POST /notes/:id/restore`; deleted notes remain stored and are excluded from normal listing.
- **Non-goals:** Permanent purge, trash listing, retention expiry, durable cross-restart storage, authentication changes, or exposing deletion metadata.

## Acceptance Criteria

- Deleting an owned note returns `204`, retains its record, and removes it from `GET /notes`.
- Restoring that note returns `204` and restores the same ID and content to `GET /notes`.
- Delete and restore are idempotent.
- Missing and foreign-owned IDs cannot be deleted or restored.
- `GET /notes` returns only active notes owned by the requester.
- Internal lifecycle metadata never appears in note responses.
- Existing create and active-list behavior remains unchanged.
- Store, route, and complete repository validation pass.

## Territory

| Constraint / convention / gate | Evidence | Bearing on the plan |
| --- | --- | --- |
| Notes live in one process-local `Map`. | `src/store/notes.js:1` | Soft deletion should retain records in this collection. |
| Listing currently filters only by owner. | `src/store/notes.js:3-4` | Add active-state filtering beside ownership filtering. |
| Creation stores and returns public note objects. | `src/store/notes.js:7-10` | Lifecycle metadata must remain internal. |
| IDs derive from map size. | `src/store/notes.js:7-10` | Retaining deleted entries avoids ID reuse caused by shrinking the map. |
| Delete checks ownership before physical removal. | `src/store/notes.js:13-15` | Replace removal with an owned state transition and mirror it for restore. |
| HTTP handlers delegate identity and parameters to the store. | `src/routes/notes.js:4-9` | Restore should remain thin framework glue. |
| Behavior and destructive ownership checks belong in the store. | `docs/conventions.md:2-3` | Both lifecycle transitions must enforce ownership below the route layer. |

## Units

### U1: Pin the lifecycle contract [executor: `test-engineer`] [risk: low]

- **Scope:** Establish an ESM test command and RED tests through exported store behavior.
- **Files:** `package.json` (new), `test/notes-store.test.js` (new)
- **Acceptance:** Tests cover delete-hide-restore, identity preservation, repeated transitions, missing IDs, ownership isolation, and unchanged create/list behavior; failures are behavioral rather than harness errors.
- **Depends on:** None.
- **Deviations contract:** Minor contradiction means choose the conservative option and log it; premise contradiction means stop and report. Never deviate silently.

### U2: Implement the store lifecycle [executor: `tdd-workflow`] [risk: high]

- **Scope:** Introduce the internal envelope, replace hard deletion, filter deleted records, and add a new ownership-aware `restoreNote` export.
- **Files:** `src/store/notes.js`, `test/notes-store.test.js` (new)
- **Acceptance:** U1 tests pass; no deletion path calls `Map.delete`; public results contain only note data; unauthorized transitions cannot change visibility.
- **Depends on:** U1.
- **Deviations contract:** Minor contradiction means choose the conservative option and log it; premise contradiction means stop and report. Never deviate silently.

### U3: Add the restore endpoint test-first [executor: `tdd-workflow`] [risk: high]

- **Scope:** Test and register `POST /notes/:id/restore` as a thin `restoreNote` caller.
- **Files:** `src/routes/notes.js`, `test/notes-routes.test.js` (new)
- **Acceptance:** The route forwards `req.user.id` and `req.params.id`, returns an empty `204`, supports repeated and unauthorized attempts safely, and preserves existing route behavior.
- **Depends on:** U2.
- **Deviations contract:** Minor contradiction means choose the conservative option and log it; premise contradiction means stop and report. Never deviate silently.

### U4: Run repository verification [executor: `verification-loop`] [risk: low]

- **Scope:** Run targeted tests followed by every repository-defined test, lint, type-check, and build gate.
- **Files:** No planned production changes.
- **Acceptance:** All applicable validators pass and the final diff contains only the planned store, route, and test-harness changes.
- **Depends on:** U2, U3.
- **Deviations contract:** Minor contradiction means choose the conservative option and log it; premise contradiction means stop and report. Never deviate silently.

## Sequencing

- **Wave 1:** U1
- **Wave 2:** U2
- **Wave 3:** U3
- **Wave 4:** U4
- **First visible result:** U2 proves through the store seam that deleted notes remain restorable while hidden. U3 exposes the complete HTTP journey.
- Parallel work is not recommended because each unit establishes the contract required by the next.

## Risks & Rollback

- **Accidental hard deletion:** Test identity-preserving restoration and prohibit `Map.delete` in the lifecycle path.
- **Cross-user restoration:** Keep ownership checks in `restoreNote` and test foreign records.
- **Metadata leakage:** Keep lifecycle state in the internal envelope and assert public response shapes.
- **Rollback:** Revert route and store lifecycle changes together. The process-local store requires no data migration.

## Open Questions

- **Q1: Must deleted notes survive process restarts?** Recommended: no, interpret survival within the existing process-local store. If required, replace this plan with durable storage, migration, and persistence tests.
- **Q2: Is permanent purge or retention required later?** Recommended: no for this feature. If accepted, deleted records remain for the process lifetime; purge policy can be designed separately.

## Evidence Log

- Read `docs/conventions.md`, `src/store/notes.js`, and `src/routes/notes.js`.
- Inspected the complete tracked tree for test, package, and CI configuration.
- Searched for existing soft-delete, restore, TODO, and ownership implementations; none were present.
- Inspected target-file history; only the baseline notes implementation exists.
- Verified the working tree remained unchanged.
