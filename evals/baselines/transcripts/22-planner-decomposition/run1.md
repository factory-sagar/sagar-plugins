# Plan: Soft-delete and Restore Notes

## Summary

Replace destructive note removal with an ownership-checked lifecycle state. Deleted notes remain stored, disappear from normal listings, and can be restored through `POST /notes/:id/restore`.

## Decisions

- **D1 — Store lifecycle metadata beside each note in the existing `Map`.** Represent entries internally as note plus deletion state, while returning only the note payload. Evidence: `src/store/notes.js:1-10`. Rejected: expose a tombstone field on note payloads, which changes API shapes / move deleted notes into a second map, which creates synchronization risk.
- **D2 — Keep filtering, ownership checks, and delete/restore transitions in the store.** Evidence: repository policy assigns behavior and destructive ownership checks to the store (`docs/conventions.md:2-3`), matching current deletion (`src/store/notes.js:13-15`). Rejected: route-layer filtering or authorization, which violates the documented boundary.
- **D3 — Make delete and restore idempotent, returning `204` without distinguishing missing, active, deleted, or foreign-owned IDs.** This preserves the existing non-disclosing delete contract (`src/routes/notes.js:6-9`). Rejected: `200` with the restored note, which adds an unrequested response contract / `403` or `404`, which exposes existence or ownership distinctions absent today.

## Goal / Non-goals

- **Goal:** Owned notes can transition between active and deleted states without losing their ID or content.
- **Non-goals:**
  - Trash/archive listing, permanent purge, retention, or deletion timestamps.
  - Durable persistence across process restarts.
  - Changes to authentication, note-body validation, or existing response payloads.

## Acceptance Criteria

- Deleting an owned active note returns `204`, removes it from `GET /notes`, but retains its record.
- `POST /notes/:id/restore` returns `204` and makes an owned deleted note visible again with the same ID and content.
- Repeated delete or restore requests are safe no-ops.
- Missing and foreign-owned IDs cannot be deleted or restored and reveal no ownership information.
- `GET /notes` returns only active notes belonging to the requesting user.
- Existing create and list response shapes remain unchanged.

## Territory

| Constraint / convention / gate | Evidence | Bearing on the plan |
| --- | --- | --- |
| Notes are held in one process-local `Map`. | `src/store/notes.js:1` | Soft-delete must retain entries in this map; restart durability requires a separate persistence plan. |
| Listing currently returns every note owned by the user. | `src/store/notes.js:3-4` | Active-state filtering belongs in `listNotes`. |
| Creation stores and returns the public note object. | `src/store/notes.js:7-10` | Lifecycle metadata should not be added to that public object. |
| Deletion currently checks ownership and removes the entry. | `src/store/notes.js:13-15` | Replace removal with an owned state transition and mirror it for restoration. |
| Route handlers are deliberately thin. | `docs/conventions.md:2`; `src/routes/notes.js:3-10` | The restore handler should only delegate and translate the result to HTTP. |
| No tracked test or package configuration exists. | Repository tree (`git ls-tree -r HEAD`) | The first implementation unit must establish a minimal executable test seam without introducing unnecessary dependencies. |
| History contains only the baseline implementation. | Commit `5184874` | There are no prior restore attempts or compatibility constraints to preserve beyond current behavior. |

## Units

### U1 — Pin the lifecycle contract [executor: `test-engineer` (TDD RED)] [risk: low]

- **Scope:** Add a minimal no-dependency test harness and failing behavior tests through the public store and route-registration seams.
- **Files:** `package.json` (new), `test/notes.test.js` (new).
- **Acceptance:**
  - Tests cover delete-hidden-restore, content/ID preservation, repeat operations, missing IDs, and cross-user isolation.
  - Route tests require registration of `POST /notes/:id/restore` and assert its `204` response.
  - The tests fail for the missing behavior rather than syntax or harness errors.
- **Depends on:** None.
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

### U2 — Implement soft-delete and restore [executor: `implementer` (TDD GREEN)] [risk: high]

- **Scope:** Refactor stored entries to own lifecycle state, filter deleted notes, replace hard deletion, add `restoreNote`, and register the restore route.
- **Files:** `src/store/notes.js`, `src/routes/notes.js`.
- **Acceptance:**
  - No deletion path calls `Map.delete`.
  - Both state transitions enforce ownership in the store.
  - Restore uses `POST /notes/:id/restore` and returns `204`.
  - All U1 tests pass without changing their behavioral expectations.
- **Depends on:** U1.
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

### U3 — Run repository verification [executor: `verification-loop`] [risk: low]

- **Scope:** Run the targeted lifecycle tests and every repository-defined lint, type, test, and build gate that exists after U1 establishes configuration.
- **Files:** No planned production changes.
- **Acceptance:** All applicable validators pass, with every changed lifecycle invariant mapped to observable test evidence.
- **Depends on:** U2.
- **Deviations contract:** minor contradiction → conservative option + log; premise contradiction → stop and report. Never deviate silently.

## Sequencing

- **Wave 1:** U1.
- **Wave 2:** U2.
- **Wave 3:** U3.
- **First visible result:** After U2, the full delete-list-restore-list journey passes through the registered route seam.
- Parallel work is not recommended because U1 and U2 share the same behavioral contract.

## Risks & Rollback

- **Accidental data loss:** retaining a `Map.delete` path would defeat restoration. Mitigate with delete-restore identity tests.
- **Authorization regression:** restoring another user’s note could expose data. Keep ownership checks in the store and test both active and deleted foreign records.
- **API leakage:** returning different statuses could disclose note existence. Preserve uniform `204` behavior.
- **Rollback:** Revert the route and store changes together. No migration or persistent-data cleanup is required for the current in-memory store.

## Open Questions

- **Q1: Must deleted notes survive process restarts?** Recommended: no, interpret “survive” as surviving deletion within the existing process-local store. If yes, this plan must expand to durable storage, migration, and persistence-adapter tests.
- **Q2: Which test runtime should establish the missing harness?** Recommended: Node’s built-in `node:test` with ESM configuration, avoiding a new dependency. If an external harness exists outside the tracked repository, use that convention instead and log the deviation.

## Evidence Log

- Read `docs/conventions.md`, `src/store/notes.js`, and `src/routes/notes.js`.
- Searched the repository for tests, restore behavior, ownership rules, TODOs, and validation configuration.
- Inspected commit `5184874` and target-file history for prior attempts or reverts.
- Confirmed the tracked tree contains only the two source modules and conventions document.
