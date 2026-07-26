# Plan: Soft-Delete and Restore Notes

## Summary

Replace physical note deletion with an internal tombstone so deleted notes remain restorable. Exclude tombstoned notes from normal listings and add `POST /notes/:id/restore`, preserving existing ownership and thin-route conventions.

## Decisions

- **D1: Keep soft-deleted notes in the existing `Map` and mark them with an internal `deletedAt` tombstone.** Evidence: notes currently live in one in-memory collection (`src/store/notes.js:1`), while deletion physically removes the owned record (`src/store/notes.js:13-15`). Rejected: separate archive map, because it splits note ownership and risks ID collisions / hard-delete plus audit log, because reconstruction would not preserve the authoritative record / boolean-only marker, because a timestamp records lifecycle state without limiting future retention policy.
- **D2: Own deletion, restoration, filtering, and authorization entirely in the store.** Evidence: documented convention places behavior in store modules and keeps handlers thin (`docs/conventions.md:2`); destructive operations require store-level ownership checks (`docs/conventions.md:3`); the existing delete handler delegates directly to the store (`src/routes/notes.js:6-8`). Rejected: ownership checks in the route, because alternate callers could bypass them / generic note-update logic, because lifecycle transitions need stricter invariants / route-level list filtering, because it would leak store internals into HTTP wiring.
- **D3: Make restore an opaque, idempotent `204 No Content` operation.** Evidence: deletion already returns `204` regardless of whether the store finds an owned note (`src/routes/notes.js:6-8`), and the store silently ignores absent or foreign records (`src/store/notes.js:14-15`). Rejected: `200` with the restored note, because it changes the lifecycle endpoint’s response pattern / `404` for absent notes, because it exposes record existence / `403` for foreign notes, because it enables ownership enumeration.

## Goal / Non-goals

- **Goal:** An authenticated owner can soft-delete a note, stop seeing it in `GET /notes`, and later restore the same note through `POST /notes/:id/restore`.
- **Non-goals:** Permanent purge, retention policies, listing deleted notes, bulk restore, changing note IDs or payload semantics, durable storage across process restarts, or unrelated authorization hardening.

## Acceptance Criteria

- Deleting an owned active note keeps its ID and original data in the store while recording deletion state.
- `GET /notes` excludes deleted notes and continues to return active notes owned by the requester.
- `POST /notes/:id/restore` clears deletion state only when the note belongs to the requester.
- A restored note reappears exactly once in `GET /notes` with its original ID and content.
- Delete and restore are idempotent; repeated calls do not corrupt data or duplicate notes.
- Restoring an active, absent, or foreign note is an opaque no-op returning `204`.
- One user cannot delete or restore another user’s note.
- Internal lifecycle metadata does not unintentionally alter the existing note response shape.
- Store and route regression tests pass under a documented test command.

## Territory

| Constraint / convention / gate | Evidence | Bearing on the plan |
| --- | --- | --- |
| Notes use process-local in-memory storage | `src/store/notes.js:1` | Soft deletion retains records in the existing map; restart durability is outside current architecture. |
| Listings currently filter only by owner | `src/store/notes.js:3-4` | Add active-state filtering alongside the ownership predicate. |
| Creation stores and returns the same note | `src/store/notes.js:7-10` | Reserve lifecycle metadata against request-body overrides and prevent accidental API leakage. |
| Delete currently hard-deletes after ownership validation | `src/store/notes.js:13-15` | Replace removal with an idempotent tombstone transition and add a symmetric restore transition. |
| Route handlers are intentionally thin | `docs/conventions.md:2` | Route work is limited to importing, registering, delegating, and responding. |
| Destructive endpoints validate ownership in the store | `docs/conventions.md:3` | Restore must use `userId` at the store boundary even though it reverses deletion. |
| Routes derive the actor from `req.user.id` | `src/routes/notes.js:4-7` | The restore handler must pass `req.user.id` and `req.params.id`; it must not trust body ownership data. |
| No tracked tests, package manifest, or CI configuration exist | Repository tree scan in Evidence Log | Establish a minimal dependency-free test seam and record the canonical command. |
| No prior restore or soft-delete attempt exists | Source history search in Evidence Log | Implementation can evolve the current model without migration or compatibility code. |

## Units

### U1: Define and test note lifecycle semantics [executor: `tdd-workflow`] [risk: high]

- **Scope:** Add failing store-level tests, then implement internal tombstoning, active-only listing, and owner-scoped restoration.
- **Files:** `src/store/notes.js`, `package.json` (new), `test/store/notes.test.js` (new).
- **Acceptance:**
  - Tests first prove that the current hard delete cannot be restored.
  - `deleteNote` tombstones only an owned active note and does not replace or remove its record.
  - `listNotes` excludes tombstoned notes.
  - `restoreNote(userId, id)` clears the tombstone only for the owner.
  - Repeated lifecycle calls are idempotent.
  - Foreign and missing IDs remain no-ops.
  - Tests use isolated users/state and do not add a production-only reset API.
  - A minimal `node:test` script provides the repository’s canonical test command.
- **Depends on:** none.
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

### U2: Add and test the restore HTTP endpoint [executor: `tdd-workflow`] [risk: high]

- **Scope:** Wire the store transition through `POST /notes/:id/restore` and verify the HTTP boundary.
- **Files:** `src/routes/notes.js`, `test/routes/notes.test.js` (new).
- **Acceptance:**
  - Route registration includes exactly `POST /notes/:id/restore`.
  - The handler calls `restoreNote(req.user.id, req.params.id)`.
  - The handler returns `204` with an empty body for restored, active, absent, and foreign notes.
  - Existing list, create, and delete registrations remain unchanged.
  - Route tests use the project’s lightweight app/response seam without introducing a web-framework dependency.
- **Depends on:** U1.
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

### U3: Run the repository gate [executor: `worker`] [risk: low]

- **Scope:** Run the canonical test command and inspect the final diff for lifecycle, ownership, and API-shape regressions.
- **Files:** No additional files expected.
- **Acceptance:**
  - All store and route tests pass.
  - The diff contains no hard deletion from the note lifecycle path.
  - No deleted note appears in normal listings.
  - No unauthorized restore changes state.
  - No unrequested purge or deleted-notes listing API is introduced.
- **Depends on:** U1, U2.
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

## Sequencing

- **Wave 1:** U1 establishes the lifecycle and regression seam.
- **Wave 2:** U2 adds the HTTP endpoint against U1’s store contract.
- **Wave 3:** U3 runs the complete gate.
- **First visible result:** U1 demonstrates that deleting a note hides it without destroying it and that restoring it returns the original note to listings.

## Risks & Rollback

- **Lifecycle metadata leaks through JSON** → keep tombstone state internal or strip it at the store’s public return boundary; test response shape.
- **Unauthorized restoration exposes note existence** → preserve opaque no-op semantics and identical `204` responses.
- **Tombstones grow memory indefinitely** → accept this under the current requirement; define retention or purge separately if needed.
- **No existing test harness** → use Node’s built-in test runner and avoid new runtime dependencies.
- **Rollback** → revert the route import/registration and store lifecycle changes together. The current in-memory model requires no schema rollback.

## Open Questions

- **Q1: Should `deletedAt` be externally visible?** Recommended: no, preserve the existing note response shape. If taken: lifecycle metadata remains a store concern and tests assert it is not serialized.
- **Q2: Must deleted notes survive process restarts?** Recommended: no, interpret “survive” as surviving deletion within the repository’s existing in-memory storage model. If restart durability is required: stop and plan a persistence layer and migration separately.
- **Q3: Should soft-deleted notes expire or be permanently purged?** Recommended: no retention policy in this feature. If taken: tombstones remain restorable indefinitely for the lifetime of the store.

## Evidence Log

- Read governing planner contract and its linked workflow documentation.
- Read `docs/conventions.md`, `src/store/notes.js`, and `src/routes/notes.js`.
- Searched the repository for delete, restore, ownership, tests, package managers, and validation configuration.
- Inspected the complete tracked tree; it contains only the convention document and two notes modules.
- Inspected source history and all branches; only the baseline notes implementation exists, with no prior soft-delete or restore attempt.
- Verified the working tree remained unchanged apart from the pre-existing untracked `.factory/` directory.
