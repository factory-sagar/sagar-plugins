# Saved Filter Import and Export

## Summary

Add JSON export and import for saved filters. Import accepts only a strict, versioned envelope and rejects malformed JSON, unsupported versions, invalid filter structures, and references to deleted fields.

## Context / Current State

**Assumptions, repository not provided:**

- Saved filters already exist as named, persisted user resources with field-ID-based filter definitions.
- A UI lists saved filters and a service/store creates or persists them.
- The application has an authenticated request context and a field catalog or repository that can distinguish active from deleted fields.
- The project has established result, schema, telemetry, storage, and test conventions. Reuse them rather than introducing new libraries.

Current behavior is assumed to support creating, listing, applying, updating, and deleting saved filters, with no portable serialized representation.

## Goals

- Export one saved filter as a deterministic JSON file.
- Import one exported filter into the current user/workspace scope.
- Reject malformed JSON.
- Reject an envelope whose version is not explicitly supported.
- Reject filters referencing fields that are deleted or unavailable in the target scope.
- Preserve typed failure behavior and avoid partial persistence.

## Non-Goals

- Bulk import or export.
- Importing arbitrary query formats, legacy unversioned objects, or future versions.
- Restoring deleted fields.
- Sharing, publishing, merging, or overwriting existing saved filters.
- Adding migrations, dual reads, or backward compatibility beyond the defined import format.

## Invariants

1. Only `version: 1` is accepted.
2. Decoded JSON remains `unknown` until the strict envelope parser refines it.
3. Import payloads are self-contained and contain no database IDs, owner IDs, workspace IDs, audit fields, or transport-specific state.
4. Every referenced field ID must resolve to an active field visible in the importing scope.
5. Import never persists a filter until all parsing, semantic validation, authorization, and field-resolution checks succeed.
6. A retry of the same import request must not create duplicate saved filters.
7. Exported and imported JSON is never logged or attached to telemetry.

## Design Constraints

Standards applied: `VOCABULARY.md`, `NAMING_AND_LAYOUT.md`, `DESIGNING_MODULES.md`, `BOUNDARIES_AND_PARSING.md`, `ERROR_HANDLING.md`, `OBSERVABILITY.md`, `ASYNC_AND_WORKFLOWS.md`, `TESTING_AND_VERIFICATION.md`, `TYPE_CONTRACTS.md`, and `tdd-workflow`.

- Reuse the repository’s existing schema parser and typed `Result` convention.
- Keep JSON parsing and file reading at the inbound UI/protocol boundary.
- Keep portable-format policy in a cohesive domain module, not the controller or persistence adapter.
- Treat field existence as a service dependency, not a client-side-only check.
- Map framework exceptions to typed failures at adapters.
- Propagate caller cancellation to file reads and persistence operations where supported.
- Use the existing telemetry mechanism only. Do not add a telemetry provider for this feature.

## Alternatives Considered

### Option 1: Export the persisted saved-filter record directly

**Rejected.** Persisted records commonly expose internal IDs, ownership, timestamps, and storage-specific shapes. It couples the public format to database schema and prevents strict semantic validation at import.

### Option 2: Accept unversioned filter JSON and infer its shape

**Rejected.** Ambiguous parsing cannot distinguish malformed or obsolete imports from valid data. It makes future format evolution unsafe and violates the explicit unknown-version rejection requirement.

### Option 3: Validate deleted fields only in the UI

**Rejected.** Client state can be stale or bypassed. The authoritative service must resolve fields in the target scope before persistence.

### Option 4: Create the filter, then asynchronously report invalid fields

**Rejected.** It creates invalid persisted state and makes failures difficult to recover from. Validation must complete before the create operation.

## Recommendation

Create a versioned portable DTO and codec owned by the saved-filter domain. Route import through an application service that:

1. Parses the JSON envelope strictly.
2. Converts the DTO into a validated import command.
3. Resolves all unique referenced field IDs against the target scope.
4. Rejects any missing, deleted, or inaccessible field.
5. Persists a new saved filter atomically with an idempotency key.
6. Returns a projection suitable for UI rendering.

Export projects a saved filter into the same DTO, serializes it with stable formatting, and returns a downloadable JSON file.

## Proposed Design

### Portable JSON format

```json
{
  "version": 1,
  "kind": "saved-filter",
  "filter": {
    "name": "Open high-priority work",
    "definition": {
      "combinator": "and",
      "clauses": [
        {
          "fieldId": "status",
          "operator": "is",
          "value": "open"
        },
        {
          "fieldId": "priority",
          "operator": "is",
          "value": "high"
        }
      ]
    }
  }
}
```

The precise `definition` schema must reuse the existing saved-filter definition parser. The portable format owns only its envelope, version, and public filter projection.

### Import behavior

- The UI accepts one `.json` file.
- The file adapter reads text and converts JSON syntax failures to `MalformedSavedFilterJson`.
- The codec strictly parses the envelope and rejects unknown root, filter, and clause properties.
- `version !== 1` returns `UnsupportedSavedFilterImportVersion`.
- The service checks that each unique field reference is active and authorized in the target scope.
- If any referenced field is deleted, missing, or inaccessible, return `ReferencedSavedFilterFieldUnavailable` without creating a filter.
- On success, create a new saved filter. Do not overwrite based on name.
- The UI displays success and refreshes the saved-filter list.

### Export behavior

- The UI requests an export for one saved-filter ID.
- The service authorizes and loads the filter.
- The codec projects it into the version-1 DTO and serializes it with stable indentation.
- The UI downloads `<sanitized-filter-name>.saved-filter.json`.
- Export does not assume that a previously valid filter will remain importable after referenced fields are later deleted.

## Domain Model and Types

```ts
/** A portable saved-filter document supported by this application version. */
export type SavedFilterExportV1 = Readonly<{
  readonly version: 1;
  readonly kind: "saved-filter";
  readonly filter: PortableSavedFilterV1;
}>;

/** Portable projection, excluding persistence and ownership metadata. */
export type PortableSavedFilterV1 = Readonly<{
  readonly name: SavedFilterName;
  readonly definition: SavedFilterDefinition;
}>;

/** Field references extracted from a valid definition. */
export type SavedFilterFieldReferences = ReadonlySet<FieldId>;

/** Stable expected failures for file and JSON intake. */
export type ReadSavedFilterImportError =
  | FileReadFailed
  | ImportFileTooLarge
  | MalformedSavedFilterJson;

/** Stable expected failures for document parsing. */
export type ParseSavedFilterImportError =
  | UnsupportedSavedFilterImportVersion
  | InvalidSavedFilterImportDocument;

/** Stable expected failures for the application import use case. */
export type ImportSavedFilterError =
  | ReadSavedFilterImportError
  | ParseSavedFilterImportError
  | ReferencedSavedFilterFieldUnavailable
  | SavedFilterImportNotAuthorized
  | SavedFilterStoreUnavailable
  | SavedFilterImportCancelled;

/** A successful import outcome. */
export type ImportedSavedFilter = Readonly<{
  readonly savedFilter: SavedFilter;
  readonly wasReplayed: boolean;
}>;
```

`FieldId`, `SavedFilterName`, `SavedFilterDefinition`, `SavedFilter`, `Principal`, and scope types are existing domain values to be confirmed during implementation.

## Types, Interfaces, and APIs

```ts
/** Strictly parses an unknown JSON value into a supported portable document. */
export function parseSavedFilterExport(
  input: unknown,
): Result<SavedFilterExportV1, ParseSavedFilterImportError>;

/** Serializes a saved filter into the supported public exchange format. */
export function serializeSavedFilterExport(
  filter: SavedFilter,
): Result<string, SerializeSavedFilterExportError>;

/** Extracts all field references from a valid saved-filter definition. */
export function collectSavedFilterFieldReferences(
  definition: SavedFilterDefinition,
): SavedFilterFieldReferences;
```

```ts
/** Resolves whether field IDs are active and usable in a target scope. */
export interface SavedFilterFields {
  resolveActive(
    scope: SavedFilterScope,
    fieldIds: ReadonlySet<FieldId>,
    options?: Readonly<{ signal?: AbortSignal }>,
  ): Promise<Result<ReadonlyMap<FieldId, ActiveFilterField>, FieldResolutionUnavailable>>;
}

/** Persists a newly imported saved filter or replays a prior completed request. */
export interface ImportedSavedFilterStore {
  createOrReplay(
    command: CreateImportedSavedFilter,
    options: Readonly<{ idempotencyKey: ImportIdempotencyKey; signal?: AbortSignal }>,
  ): Promise<Result<ImportedSavedFilter, SavedFilterStoreUnavailable>>;
}
```

```ts
/** Application use case, called only with parsed service inputs. */
export interface ImportSavedFilter {
  import(
    command: ImportSavedFilterCommand,
    options?: Readonly<{ signal?: AbortSignal }>,
  ): Promise<Result<ImportedSavedFilter, ImportSavedFilterError>>;
}

export type ImportSavedFilterCommand = Readonly<{
  readonly actor: Principal;
  readonly scope: SavedFilterScope;
  readonly document: SavedFilterExportV1;
  readonly idempotencyKey: ImportIdempotencyKey;
}>;
```

```ts
/** Inbound UI/file adapter contract. */
export interface SavedFilterImportFileReader {
  readJson(
    file: File,
    options?: Readonly<{ signal?: AbortSignal }>,
  ): Promise<Result<unknown, ReadSavedFilterImportError>>;
}
```

The file reader owns byte-limit enforcement and `JSON.parse` exception classification. `parseSavedFilterExport` owns document-shape and version validation.

## Seams, Boundaries, Adapters, and Implementations

| Owner | Responsibility | Boundary values |
|---|---|---|
| Saved-filter codec domain module | Strict portable schema, field-reference extraction, export projection | `unknown` to `SavedFilterExportV1`; `SavedFilter` to JSON text |
| Browser file adapter | File size check, text read, JSON syntax classification | `File` to `unknown` |
| Import service | Authorization, active-field validation, idempotency, typed orchestration | refined document to `ImportedSavedFilter` |
| Field catalog/repository adapter | Scope-aware active-field lookup | field IDs to active field records |
| Saved-filter persistence adapter | Transactional create-or-replay | import command to saved filter |
| UI controller/component | User selection, feedback, list refresh, browser download | browser events to parsed service inputs |

The codec must not know browser APIs, HTTP responses, database rows, or telemetry. The persistence adapter must not accept raw JSON or browser `File` objects.

## Call Stacks and Data Flow

### Current / Old Flow

```txt
Saved-filter UI
  -> existing create/update/list/apply behavior
  -> saved-filter service/store
  -> persistence
```

There is no current portable serialization path.

### Proposed / New Flow

#### Export

```txt
Saved-filter UI export action
  -> exportSavedFilter(savedFilterId)
  -> authorize and load saved filter
  -> serializeSavedFilterExport(savedFilter)
  -> browser download adapter creates Blob and object URL
  -> user receives .saved-filter.json
```

#### Import

```txt
User chooses JSON file
  -> SavedFilterImportFileReader.readJson(file, { signal })
  -> parseSavedFilterExport(rawJson)
  -> UI creates ImportSavedFilterCommand with actor, scope, idempotency key
  -> ImportSavedFilterService.import(command, { signal })
  -> authorize import for scope
  -> collectSavedFilterFieldReferences(definition)
  -> SavedFilterFields.resolveActive(scope, fieldIds, { signal })
  -> reject unavailable/deleted field IDs, or
  -> ImportedSavedFilterStore.createOrReplay(command, { idempotencyKey, signal })
  -> protocol/UI projection
  -> success message and refreshed saved-filter list
```

### Failure Flow

```txt
File read failure
  -> FileReadFailed
  -> UI renders safe "Could not read import file" feedback

Invalid JSON syntax
  -> MalformedSavedFilterJson
  -> UI renders "Import file is not valid JSON"

Strict envelope/schema failure
  -> InvalidSavedFilterImportDocument
  -> UI renders "Import file is not a supported saved-filter export"

Unsupported version
  -> UnsupportedSavedFilterImportVersion { receivedVersion }
  -> UI renders supported-version feedback

Any referenced deleted, missing, or inaccessible field
  -> ReferencedSavedFilterFieldUnavailable { unavailableFieldIds }
  -> no persistence call
  -> UI renders rejection feedback

Store dependency failure
  -> SavedFilterStoreUnavailable
  -> existing boundary error-reporting and recoverable UI state
```

Only stable error tags, received version, count of referenced fields, and count of unavailable fields are safe for telemetry. Do not expose raw JSON or raw clause values in errors or logs.

### Retry / Cancellation / Idempotency Flow

- Generate one `ImportIdempotencyKey` when the user initiates an import. Reuse it only while retrying the same selected file submission.
- Persist or enforce the key in the same transaction as saved-filter creation, using the project’s established request-deduplication mechanism.
- A repeated request with the same key returns the original saved filter with `wasReplayed: true`.
- Do not retry malformed JSON, unsupported versions, invalid documents, authorization failures, or unavailable fields.
- Dependency failures may be retried only by the existing UI/request retry policy, using the same idempotency key.
- Passing an `AbortSignal` from the UI must cancel file reading, field lookup, and persistence where those adapters support cancellation.
- Cancellation is returned as `SavedFilterImportCancelled`, never wrapped as a store failure.

### Observability Flow

Use existing correlation and telemetry hooks at the UI/protocol and service boundaries.

Suggested safe events:

```txt
saved_filter_export_completed { savedFilterId, version: 1 }
saved_filter_import_completed { version: 1, referencedFieldCount, wasReplayed }
saved_filter_import_rejected { errorTag, version?, unavailableFieldCount? }
saved_filter_import_failed { errorTag, operation: "importSavedFilter" }
```

Do not log the selected filename, raw JSON, filter name, clause values, exception payloads, or stored filter object unless existing privacy rules explicitly classify them as safe.

## Files to Add / Change / Delete

Repository paths are assumptions and must be mapped to local conventions before implementation.

| Change | Assumed owner | Responsibility |
|---|---|---|
| Add `saved-filter-export.ts` | Saved-filter domain module | `SavedFilterExportV1`, strict parser, serializer, field-reference collector |
| Add `saved-filter-export.test.ts` | Domain tests | Codec examples and round-trip/property coverage |
| Change saved-filter import service | Application service | Scope authorization, active-field resolution, idempotent create-or-replay |
| Change field catalog/repository | Existing field adapter | Batch active-field resolution in target scope |
| Change saved-filter persistence adapter | Storage adapter | Transactional idempotent create-or-replay support |
| Change saved-filter UI | UI feature component/controller | Import file chooser, export action, typed feedback, list refresh |
| Add browser file adapter tests | UI/protocol tests | File reading, size guard, malformed JSON mapping |
| Add migration only if absent | Persistence schema | Idempotency record or uniqueness mechanism required by existing conventions |

No files are deleted.

## RGR TDD Test Plan

### Slice 1: Strict portable codec

**RED:** Given a valid saved filter, when serialized and parsed, then the parsed document equals the canonical version-1 projection.

Add failure cases for malformed envelopes, unknown properties, missing `kind`, non-`1` version, and invalid existing filter definitions.

**GREEN:** Implement the codec using the existing schema parser and saved-filter definition parser.

**REFACTOR:** Extract only codec-local projection helpers if needed.

### Slice 2: Deleted-field rejection

**RED:** Given a valid parsed import document that references one deleted field, when imported into a scope, then it returns `ReferencedSavedFilterFieldUnavailable` and records no persisted filter.

Use a recording or in-memory field seam and saved-filter store supplied through the production service dependency boundary.

**GREEN:** Extract field references, batch-resolve active fields, and guard persistence behind the result.

**REFACTOR:** Deduplicate field IDs before lookup while preserving the error’s deterministic ordering.

### Slice 3: Successful import

**RED:** Given an authorized user, active referenced fields, and a valid v1 document, when imported, then a new saved filter with the imported name and definition is persisted and returned.

**GREEN:** Implement orchestration and storage creation.

**REFACTOR:** Keep authorization and field-resolution policy in the import service.

### Slice 4: Retry safety

**RED:** Given the same import command and idempotency key submitted twice, when the store is invoked twice, then exactly one logical saved filter exists and the second response has `wasReplayed: true`.

**GREEN:** Add transactional create-or-replay behavior using the project’s established persistence pattern.

**REFACTOR:** Run this against a representative local database if uniqueness or transaction behavior is database-dependent.

### Slice 5: UI boundary behavior

**RED:** Given an invalid JSON file, when selected for import, then the UI displays the typed malformed-JSON message and never calls the import service.

**GREEN:** Implement the file reader and UI error mapping.

**REFACTOR:** Verify cancellation and disabled-state cleanup through the user-facing UI seam.

### Completion validation

Run the repository’s targeted tests for each slice, then its canonical formatter, lint, typecheck, test suite, and applicable representative persistence/runtime tests. Do not use module mocks or method spies.

## Risks and Open Questions

1. **Saved-filter definition shape:** Confirm the existing definition grammar, especially nested groups, operators, and how field references are represented.
   - Recommended answer: reuse the current parser and expose one canonical field-reference collector.

2. **Field availability semantics:** Confirm whether “deleted” includes archived, hidden, permission-revoked, or cross-workspace fields.
   - Recommended answer: reject any field that cannot be actively resolved and authorized in the target import scope.

3. **Ownership scope:** Confirm whether filters are personal, workspace-scoped, project-scoped, or mixed.
   - Recommended answer: import into the currently selected scope, never accept scope identifiers from the file.

4. **Idempotency infrastructure:** Confirm whether the repository already has request-key replay storage.
   - Recommended answer: extend the existing mechanism; otherwise add a transactionally unique `(scope, actor, idempotencyKey)` record.

5. **Import file-size limit:** Confirm the application’s existing client upload or file-read limit.
   - Recommended answer: reuse it; if absent, add a documented bounded limit before `File.text()`.

6. **Filename and download helper:** Confirm the project’s browser-download abstraction and filename sanitization convention.
   - Recommended answer: reuse it, with a fixed `.saved-filter.json` suffix.

7. **Privacy classification:** Confirm whether filter names and clause values are telemetry-safe.
   - Recommended answer: treat both as unsafe by default and emit only tags, counts, and IDs already classified safe.

**Deviations: none.**
