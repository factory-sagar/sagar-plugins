# Saved Filter JSON Import and Export

## Summary

Add versioned JSON export and import for saved filters. Imports parse untrusted input strictly, reject malformed JSON, unsupported versions, and references to deleted fields before any saved filter is created.

## Context / Current State

Saved filters exist, but repository layout, filter domain shape, field lifecycle API, protocol, and UI conventions are unavailable.

**Assumptions**

- A saved filter has a user-visible name and a structured definition containing field references.
- The application can resolve field IDs and distinguish active from deleted fields.
- Saved filters already have an authenticated owner scope.

## Goals

- Export one saved filter as portable JSON.
- Import a valid exported filter.
- Reject malformed JSON.
- Reject unknown document versions.
- Reject filters referencing deleted fields.
- Keep invalid imports side-effect free.

## Non-Goals

- Importing arbitrary legacy filter formats.
- Bulk import/export.
- Restoring deleted fields.
- Automatic field remapping.
- Changing saved-filter persistence.

## Invariants

- Only an accepted, known document version reaches domain conversion.
- Every referenced field must resolve as active at import time.
- An import rejection creates no saved filter.
- Exported documents contain a canonical public projection, never persistence-only or owner data.
- Imported filters are owned by the authenticated importing principal, never by an ID in the document.

## Design Constraints

Standards applied: boundaries and parsing, typed failures, deep modules, type contracts, observability, testing and verification, RGR TDD workflow.

- JSON text and decoded values are `unknown` until parsed.
- Expected import failures use a precise typed result union.
- The domain module owns version dispatch and field-reference extraction.
- Protocol and persistence DTOs remain separate.
- Existing repository schema, result, auth, telemetry, and test conventions must be used after repository discovery.

## Alternatives Considered

### Option 1: Client-side JSON validation and direct persistence

The UI parses JSON, validates fields, then writes through an existing saved-filter API.

**Rejected:** validation and deleted-field enforcement would be bypassable by other clients, and raw serialized input would leak across layers.

### Option 2: Versioned import/export domain service with field-resolution seam

A server-side service parses the document, selects a known version codec, resolves referenced fields, creates the filter, and projects typed failures to the protocol.

**Recommended:** centralizes portability, version dispatch, active-field validation, and atomicity behind a small interface.

### Option 3: Persist import files and process them asynchronously

Upload a document, enqueue a job, and later report import status.

**Rejected:** one-filter synchronous import does not require durable workflow infrastructure. It adds status, retry, and cancellation semantics outside the stated scope.

## Recommendation

Implement Option 2: a `SavedFilterTransfer` service with explicit JSON document codecs and narrow `SavedFilters` and `Fields` dependencies.

## Proposed Design

### Domain Model and Types

```ts
type SavedFilterExportDocument = SavedFilterExportV1;

type SavedFilterExportV1 = {
  readonly kind: "saved-filter";
  readonly version: 1;
  readonly filter: ExportedSavedFilterV1;
};

type ExportedSavedFilterV1 = {
  readonly name: SavedFilterName;
  readonly definition: SavedFilterDefinitionV1;
};

// Must be replaced with the existing canonical filter-definition domain type
// after repository discovery. It must expose referenced field IDs.
type SavedFilterDefinitionV1 = unknown;

type FieldId = string & { readonly __brand: "FieldId" };
type SavedFilterName = string & { readonly __brand: "SavedFilterName" };

type ActiveField = {
  readonly id: FieldId;
};

type ImportSavedFilterInput = {
  readonly actor: SavedFilterOwner;
  readonly jsonText: string;
};

type ImportedSavedFilter = {
  readonly savedFilter: SavedFilter;
  readonly version: 1;
};
```

The `filter` projection intentionally excludes:

- saved-filter IDs;
- owner IDs;
- creation and update timestamps;
- database-specific metadata;
- deleted-field state;
- internal-only filter properties.

### Types, Interfaces, and APIs

```ts
type ImportSavedFilterError =
  | MalformedSavedFilterJson
  | InvalidSavedFilterDocument
  | UnsupportedSavedFilterVersion
  | DeletedFieldReference
  | FieldLookupUnavailable
  | SavedFilterCreateFailed;

type MalformedSavedFilterJson = {
  readonly _tag: "MalformedSavedFilterJson";
  readonly message: "Saved filter import is not valid JSON";
};

type InvalidSavedFilterDocument = {
  readonly _tag: "InvalidSavedFilterDocument";
  readonly message: "Saved filter import has an invalid document shape";
};

type UnsupportedSavedFilterVersion = {
  readonly _tag: "UnsupportedSavedFilterVersion";
  readonly version: number | string | undefined;
  readonly message: "Saved filter import version is not supported";
};

type DeletedFieldReference = {
  readonly _tag: "DeletedFieldReference";
  readonly fieldIds: ReadonlyArray<FieldId>;
  readonly message: "Saved filter references deleted fields";
};

type FieldsForSavedFilterImport = {
  findActiveByIds(
    actor: SavedFilterOwner,
    fieldIds: ReadonlyArray<FieldId>,
    signal?: AbortSignal,
  ): Promise<Result<ReadonlyArray<ActiveField>, FieldLookupUnavailable>>;
};

type SavedFiltersForTransfer = {
  create(
    input: CreateSavedFilterInput,
    signal?: AbortSignal,
  ): Promise<Result<SavedFilter, SavedFilterCreateFailed>>;
};

class SavedFilterTransfer {
  constructor(
    private readonly fields: FieldsForSavedFilterImport,
    private readonly savedFilters: SavedFiltersForTransfer,
  ) {}

  export(savedFilter: SavedFilter): SavedFilterExportDocument;

  import(
    input: ImportSavedFilterInput,
    signal?: AbortSignal,
  ): Promise<Result<ImportedSavedFilter, ImportSavedFilterError>>;
}
```

```ts
function parseSavedFilterExportDocument(
  input: unknown,
): Result<SavedFilterExportDocument, InvalidSavedFilterDocument | UnsupportedSavedFilterVersion>;

function parseSavedFilterImportJson(
  jsonText: string,
): Result<unknown, MalformedSavedFilterJson>;

function referencedFieldIds(
  definition: SavedFilterDefinitionV1,
): ReadonlyArray<FieldId>;
```

The document parser must reject unknown top-level and V1 filter-object keys unless the existing export contract has an explicitly extensible metadata object.

### Seams, Boundaries, Adapters, and Implementations

| Owner | Responsibility | Must not know |
|---|---|---|
| `saved-filter-transfer` domain/service module | Version dispatch, parsed document conversion, field-reference verification, import orchestration | HTTP, UI, database row shapes |
| `saved-filter-export-v1` domain module | V1 codec, strict parsing, public export projection, field-ID extraction | Persistence and protocol details |
| Saved-filter repository adapter | Create imported filter under authenticated owner | Raw JSON and document-version policy |
| Field repository adapter | Resolve active fields in owner-visible scope | JSON format and saved-filter creation |
| HTTP/RPC adapter | Parse request DTO, authorize actor, map typed outcomes to response | Filter-definition internals |
| UI adapter | Trigger download, select file/text, display typed import outcomes | Persistence or field lookup |

The existing saved-filter repository should be extended only if it already cohesively owns creation. Otherwise, create a narrow transfer-specific persistence adapter.

## Call Stacks and Data Flow

### Current / Old Flow

```txt
Saved filter creation/editing
  -> protocol request DTO
  -> existing saved-filter command parser
  -> saved-filter service
  -> persistence adapter
  -> saved filter response projection
```

There is no portable export/import flow.

### Proposed / New Flow: Export

```txt
authenticated export entrypoint
  -> parse saved-filter ID request DTO
  -> authorize owner access using existing saved-filter lookup
  -> SavedFilterTransfer.export(savedFilter)
  -> SavedFilterExportV1.project(savedFilter)
  -> JSON.stringify(document)
  -> protocol response / browser download
```

The export action must use the existing saved-filter lookup and authorization path. It may export only the caller's accessible filter.

### Proposed / New Flow: Import

```txt
raw request body or uploaded text
  -> protocol parser: { jsonText: string }
  -> authenticated SavedFilterOwner
  -> SavedFilterTransfer.import({ actor, jsonText }, request.signal)
  -> JSON.parse to unknown
  -> parseSavedFilterExportDocument(unknown)
  -> SavedFilterDefinitionV1 and referencedFieldIds
  -> FieldsForSavedFilterImport.findActiveByIds(actor, fieldIds)
  -> reject if returned active IDs do not equal referenced IDs
  -> SavedFiltersForTransfer.create({ owner: actor, ...parsedFilter })
  -> ImportedSavedFilter
  -> protocol projection
```

Field validity must be checked immediately before creation. If the repository supports transactions or a database query that enforces active fields, both validation and creation should execute atomically to prevent a field being deleted between lookup and insert.

### Failure Flow

```txt
JSON.parse failure
  -> MalformedSavedFilterJson
  -> protocol 4xx validation response
  -> no field lookup, no create

strict document parse failure
  -> InvalidSavedFilterDocument
  -> protocol 4xx validation response
  -> no field lookup, no create

unknown version
  -> UnsupportedSavedFilterVersion
  -> protocol 4xx validation response
  -> no field lookup, no create

missing or deleted referenced field
  -> DeletedFieldReference(fieldIds)
  -> protocol 4xx domain response
  -> no create

field dependency failure
  -> FieldLookupUnavailable
  -> existing dependency-failure response
  -> no create

create adapter failure
  -> SavedFilterCreateFailed
  -> existing dependency-failure response
```

The exact HTTP/RPC status and public error envelope must follow repository convention. `DeletedFieldReference` should not reveal field names or identifiers that the caller is not permitted to inspect.

### Retry / Cancellation / Idempotency Flow

```txt
request AbortSignal
  -> SavedFilterTransfer.import
  -> field lookup and create adapter
```

- Propagate caller-owned cancellation to both adapters.
- Import is not idempotent by default, each successful request creates a saved filter.
- Do not add retry logic. A retried client request may create a duplicate unless the existing saved-filter API already provides an idempotency mechanism.
- If an existing idempotency-key convention exists for creates, use it at the protocol boundary and pass its refined value to the create adapter.

### Observability Flow

```txt
protocol handler
  -> existing request correlation mechanism
  -> import outcome telemetry
```

Record only safe fields:

```ts
{
  operation: "importSavedFilter",
  documentVersion: 1,
  referencedFieldCount: fieldIds.length,
  outcome: "accepted" | "rejected",
  errorTag?: ImportSavedFilterError["_tag"],
}
```

Never log raw JSON, full filter definitions, arbitrary parse causes, or field values.

## Files to Add / Change / Delete

Exact paths are repository-dependent. Map these logical modules onto the discovered local module layout and colocate tests per repository convention.

| Action | Logical module | Responsibility |
|---|---|---|
| Add | `saved-filter-export-v1` | V1 document type, strict parser, export projection, referenced-field extraction |
| Add | `saved-filter-transfer` | Export and import service, typed errors, active-field verification |
| Change | existing saved-filter domain module | Expose canonical definition projection or field-reference traversal if not already available |
| Change | existing field repository/service | Provide owner-scoped active-field resolution, preferably transaction-capable |
| Change | existing saved-filter repository/service | Accept parsed import creation input and preserve owner assignment |
| Change | saved-filter protocol adapter | Export endpoint/action, import endpoint/action, protocol projections |
| Change | saved-filter UI | Export download control and import selection/submission/error display |
| Add | `saved-filter-export-v1.test` | Codec/parser/projection behavior |
| Add | `saved-filter-transfer.test` | Service behavior through recording field and saved-filter adapters |
| Change/Add | protocol integration test | Authenticated import/export round trip and public failure envelope |
| Delete | None | No deletion is required |
| Config/Migration | None expected | Confirm no schema changes are necessary after repository discovery |

## RGR TDD Test Plan

### Slice 1: Canonical V1 export

**Behavior:** Given an accessible saved filter, when a user exports it, then the response/download is canonical V1 JSON containing only portable filter data.

1. **RED:** Protocol or service behavior test asserts `{ kind: "saved-filter", version: 1, filter }` and excludes identity, ownership, timestamps, and persistence metadata.
2. **GREEN:** Add the V1 projection and export operation.
3. **REFACTOR:** Consolidate field-definition projection only if existing domain code duplicates it.

### Slice 2: Valid V1 import

**Behavior:** Given valid V1 JSON referencing active fields, when an authorized user imports it, then one saved filter is created for that user.

1. **RED:** Service test supplies a recording active-field adapter and recording saved-filter adapter, then asserts the created input and imported result.
2. **GREEN:** Parse V1 and create through the existing saved-filter creation seam.
3. **REFACTOR:** Extract a pure document-to-create-input conversion only when it removes real duplication.

### Slice 3: Malformed JSON rejection

**Behavior:** Given malformed JSON, when a user imports it, then the result is `MalformedSavedFilterJson` and no adapter observes a create.

1. **RED:** Test invalid JSON syntax through the import public interface.
2. **GREEN:** Classify `JSON.parse` failure at the transfer boundary.
3. **REFACTOR:** None unless error construction duplicates another parser boundary.

### Slice 4: Unknown-version rejection

**Behavior:** Given structurally valid JSON with an unknown version, when imported, then the result is `UnsupportedSavedFilterVersion` and no lookup or create occurs.

1. **RED:** Test a future integer version and a non-integer version shape.
2. **GREEN:** Add strict version dispatch before V1 conversion.
3. **REFACTOR:** Keep one codec registry or exhaustive dispatch, not parallel conditionals.

### Slice 5: Deleted-field rejection

**Behavior:** Given valid V1 JSON referencing a deleted or absent field, when imported, then the result is `DeletedFieldReference` and no saved filter is created.

1. **RED:** Recording field adapter returns fewer active fields than requested; assert the rejected ID set and zero create records.
2. **GREEN:** Compare canonical requested and resolved IDs before creation.
3. **REFACTOR:** Centralize duplicate-ID normalization only if filter definitions can contain repeated references.

### Slice 6: Boundary and protocol behavior

**Behavior:** Given authenticated export/import requests, the protocol returns the repository-standard success and typed validation-error envelopes.

1. **RED:** Integration test through the real handler/router and representative local persistence/runtime where available.
2. **GREEN:** Add protocol parsing, projections, auth reuse, and browser/download response behavior.
3. **REFACTOR:** Keep error-to-protocol mapping at the adapter boundary.

### Additional verification

- Property test: every valid V1 document emitted by `export` parses as V1.
- Parser tests: reject non-object roots, missing keys, unknown keys, wrong `kind`, invalid names, invalid definition shapes, and malformed field IDs.
- Persistence/runtime test: if active-field validation and insertion share a transaction, test deletion/race semantics with the representative database.
- Run the repository’s targeted test command per slice, then its canonical lint, typecheck, full test suite, and build checks.

## Risks and Open Questions

1. **Saved-filter definition shape:** The actual definition, nested field-reference locations, and supported operators are unknown. The V1 codec must reuse existing domain parsing rather than duplicate it.
2. **Deleted-field semantics:** Confirm whether a field can be hidden, archived, inaccessible, or hard-deleted, and which states must produce `DeletedFieldReference`.
3. **Authorization:** Confirm whether field lookup must enforce both ownership and read access. The recommended contract assumes it does.
4. **Atomicity:** Confirm whether the data store can validate active fields and create a filter in one transaction. If not, document the deletion race and use the narrowest available locking/constraint mechanism.
5. **Name conflicts:** The desired behavior when an imported name duplicates an existing saved filter is unspecified. Reuse existing create semantics; do not invent rename, overwrite, or deduplication behavior.
6. **Transport/UI conventions:** Endpoint shape, file-download mechanics, upload size limits, and error copy must follow repository precedent.
7. **Observability:** Reuse existing telemetry if present. No new telemetry system should be introduced for this feature.

**Deviations: none.**
