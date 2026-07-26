# Saved Filter JSON Import and Export

## Summary

Add authenticated JSON export and import for saved filters. Export emits a versioned, portable document. Import parses untrusted JSON, rejects malformed JSON, unsupported versions, invalid filter structures, and references to deleted fields before creating a saved filter.

## Context / Current State

Repository details were not provided. This spec assumes saved filters already exist, are user-owned, persist a name plus filter definition, and have a field catalog or schema that can determine which fields remain active.

## Goals

- Export one saved filter as a deterministic, versioned JSON document.
- Import a document to create a new saved filter.
- Reject malformed JSON.
- Reject unknown document versions.
- Reject filters referencing deleted fields.
- Preserve existing authorization and saved-filter creation rules.

## Non-Goals

- Bulk import/export.
- Sharing filters between users or workspaces.
- Migrating legacy unversioned documents.
- Restoring deleted field definitions.
- Automatic field-name remapping.
- Changing existing filter semantics or query execution.

## Invariants

- JSON text is an Unknown Boundary Input until parsed.
- Only `version: 1` is accepted.
- Imported filters may reference only active fields visible to the importing principal.
- No saved filter is created when import validation fails.
- Export never includes persistence IDs, owner IDs, audit fields, or internal metadata.
- Expected failures use typed result values internally, with HTTP/UI translation at the boundary.
- Import is retry-safe when the client supplies an idempotency key.

## Design Constraints

- Reuse the repository’s existing schema parser, result type, authorization, persistence transaction, logging, and test conventions.
- Strictly parse mutable/imported document objects, rejecting unknown keys.
- Do not cast `JSON.parse` output to a domain type.
- Keep field-liveness validation and persistence in one transaction or equivalent consistency boundary.
- Log only safe tags, saved-filter IDs, field IDs, version, and request correlation data. Never log raw imported JSON.

Standards applied: `TYPE_CONTRACTS.md`, `BOUNDARIES_AND_PARSING.md`, `ERROR_HANDLING.md`, `ASYNC_AND_WORKFLOWS.md`, `OBSERVABILITY.md`, `TESTING_AND_VERIFICATION.md`, `DESIGNING_MODULES.md`.

## Alternatives Considered

### Option 1: Reuse persisted saved-filter JSON as the export format

**Rejected.** Persistence rows leak internal identifiers and couple the public format to schema evolution. They also cannot safely represent a portable versioning contract.

### Option 2: Parse JSON in the UI, then submit typed filter data

**Rejected.** Client-side validation is useful for UX but cannot enforce authorization, version support, deleted-field rejection, or race-safe persistence. The server must own the canonical parser.

### Option 3: Translate imported field IDs automatically

**Rejected.** Deleted-field references must be rejected by product requirement. Silent remapping could change query meaning.

### Option 4: Version-specific codec with a current canonical domain model

**Recommended.** A versioned document codec owns serialized compatibility, while the existing saved-filter domain model remains canonical.

## Recommendation

Introduce a `SavedFilterDocumentV1` codec and an `ImportSavedFilter` service operation. The import service parses text, decodes the versioned document, authorizes the actor, validates all referenced fields against active field metadata in the same transaction that creates the filter, then returns the created saved filter.

## Proposed Design

### Export format

```json
{
  "version": 1,
  "name": "My open deals",
  "filter": {
    "operator": "and",
    "clauses": [
      {
        "fieldId": "deal-stage",
        "operator": "equals",
        "value": "open"
      }
    ]
  }
}
```

The exact `filter` shape must be the existing canonical serialized projection of the filter AST. It must use stable field identifiers, not display labels.

### Import behavior

1. Receive text plus optional idempotency key.
2. Parse JSON text to `unknown`.
3. Decode strict versioned document.
4. Convert the document filter projection to the existing domain `FilterDefinition`.
5. Authorize creation for the target scope.
6. Start a transaction.
7. Load referenced fields using the active-field query, scoped to the actor’s accessible workspace/entity.
8. Reject if any referenced field is absent, deleted, or inaccessible.
9. Create the saved filter through the existing domain/service creation path.
10. Persist and commit.
11. Project the created filter to the existing API response.

## Domain Model and Types

```ts
type SavedFilterDocumentV1 = Readonly<{
  readonly version: 1;
  readonly name: SavedFilterName;
  readonly filter: SavedFilterFilterDtoV1;
}>;

type SavedFilterExportDocument = SavedFilterDocumentV1;

type ImportSavedFilterInput = Readonly<{
  readonly documentText: string;
  readonly idempotencyKey?: IdempotencyKey;
}>;

type ImportSavedFilterResult =
  | Readonly<{ readonly _tag: "imported"; readonly savedFilter: SavedFilter }>
  | Readonly<{ readonly _tag: "replayed"; readonly savedFilter: SavedFilter }>;

type SavedFilterImportError =
  | InvalidSavedFilterJson
  | UnsupportedSavedFilterDocumentVersion
  | InvalidSavedFilterDocument
  | DeletedFieldReference
  | SavedFilterImportNotAuthorized
  | SavedFilterNameConflict
  | SavedFilterStoreUnavailable;
```

```ts
class InvalidSavedFilterJson extends Error {
  readonly _tag = "InvalidSavedFilterJson" as const;
}

class UnsupportedSavedFilterDocumentVersion extends Error {
  readonly _tag = "UnsupportedSavedFilterDocumentVersion" as const;

  constructor(readonly receivedVersion: unknown) {
    super("Unsupported saved-filter document version");
  }
}

class DeletedFieldReference extends Error {
  readonly _tag = "DeletedFieldReference" as const;

  constructor(readonly fieldIds: ReadonlyArray<FieldId>) {
    super("Imported filter references deleted or unavailable fields");
  }
}
```

`DeletedFieldReference` intentionally does not distinguish deleted from inaccessible fields in the user-facing response, preventing metadata disclosure. Safe telemetry may record only the count of rejected IDs unless existing authorization policy permits field IDs.

## Types, Interfaces, and APIs

```ts
/**
 * Encodes one saved filter into the public, portable v1 JSON document.
 */
function toSavedFilterDocumentV1(savedFilter: SavedFilter): SavedFilterDocumentV1;

/**
 * Parses untrusted JSON text into a refined versioned document.
 */
function parseSavedFilterDocument(
  documentText: string,
): Result<SavedFilterDocumentV1, InvalidSavedFilterJson | UnsupportedSavedFilterDocumentVersion | InvalidSavedFilterDocument>;

/**
 * Reconstructs the canonical filter definition from the v1 DTO.
 */
function parseSavedFilterFilterDtoV1(
  dto: SavedFilterFilterDtoV1,
): Result<FilterDefinition, InvalidSavedFilterDocument>;
```

```ts
type FieldsForSavedFilterImport = {
  findActiveAccessibleByIds(
    actor: SavedFilterActor,
    fieldIds: ReadonlySet<FieldId>,
    options: { readonly signal?: AbortSignal },
  ): Promise<Result<ReadonlySet<FieldId>, FieldCatalogUnavailable>>;
};

type SavedFilterImportStore = {
  transaction<T>(
    operation: (tx: SavedFilterImportTransaction) => Promise<Result<T, SavedFilterStoreUnavailable>>,
    options: { readonly signal?: AbortSignal },
  ): Promise<Result<T, SavedFilterStoreUnavailable>>;
};

type SavedFilterImportTransaction = {
  create(
    input: CreateSavedFilterInput,
  ): Promise<Result<SavedFilter, SavedFilterNameConflict | SavedFilterStoreUnavailable>>;

  findIdempotencyReplay(
    key: IdempotencyKey,
  ): Promise<Result<SavedFilter | undefined, SavedFilterStoreUnavailable>>;

  recordIdempotencyResult(
    key: IdempotencyKey,
    documentHash: DocumentHash,
    savedFilterId: SavedFilterId,
  ): Promise<Result<void, SavedFilterStoreUnavailable>>;
};
```

```ts
interface SavedFilterImportService {
  import(
    actor: SavedFilterActor,
    input: ImportSavedFilterInput,
    options: { readonly signal?: AbortSignal },
  ): Promise<Result<ImportSavedFilterResult, SavedFilterImportError>>;
}
```

### HTTP contract

```http
POST /saved-filters/import
Content-Type: application/json
Idempotency-Key: optional-key
```

```json
{ "documentText": "{\"version\":1,\"name\":\"...\",\"filter\":{...}}" }
```

Success:

```http
201 Created
Content-Type: application/json
```

```json
{
  "savedFilter": {
    "id": "new-saved-filter-id",
    "name": "My open deals",
    "filter": { "...": "existing API projection" }
  }
}
```

Expected failures:

| Error | HTTP status |
|---|---:|
| `InvalidSavedFilterJson` | 400 |
| `InvalidSavedFilterDocument` | 400 |
| `UnsupportedSavedFilterDocumentVersion` | 422 |
| `DeletedFieldReference` | 422 |
| `SavedFilterImportNotAuthorized` | existing authorization convention, typically 403 |
| `SavedFilterNameConflict` | existing conflict convention, typically 409 |
| `SavedFilterStoreUnavailable` | 503 or existing dependency-failure mapping |

```http
GET /saved-filters/:savedFilterId/export
Accept: application/json
```

Success returns `SavedFilterDocumentV1` with:

```http
200 OK
Content-Type: application/json
Content-Disposition: attachment; filename="saved-filter-<safe-slug>.json"
Cache-Control: no-store
```

The API must project the document, then serialize with `JSON.stringify`. It must not expose raw persistence records.

## Seams, Boundaries, Adapters, and Implementations

| Owner | Responsibility |
|---|---|
| `saved-filter-document-v1` domain module | Strict DTO parsing, version discrimination, filter projection and reconstruction. No I/O. |
| Existing filter domain module | Canonical AST invariants, field-ID collection, and creation input validation. |
| `ImportSavedFilter` service module | Coordinates parsing result, authorization, active-field validation, transaction, idempotency, and typed failure classification. |
| Existing field-catalog adapter | Queries active, actor-accessible fields. It must not return deleted fields. |
| Existing saved-filter persistence adapter | Implements transaction, filter creation, and idempotency storage. |
| HTTP/controller adapter | Parses request body, obtains actor, propagates cancellation, maps typed results to HTTP. |
| UI import/export feature | Reads local file text, invokes HTTP API, downloads export. Client validation is advisory only. |

The field catalog and persistence adapters are real seams because they cross authorization and database boundaries. The pure document codec does not need an adapter.

## Call Stacks and Data Flow

### Current / Old Flow

```txt
User -> existing saved-filter UI/API -> existing create/read flow
```

There is no portable serialized document contract.

### Proposed / New Export Flow

```txt
User clicks Export
  -> UI requests GET /saved-filters/:id/export
  -> HTTP adapter authenticates and authorizes read access
  -> existing SavedFilterRepository loads saved filter
  -> toSavedFilterDocumentV1(savedFilter)
  -> JSON.stringify(document)
  -> protocol adapter returns attachment response
  -> browser downloads .json file
```

### Proposed / New Import Flow

```txt
User selects JSON file
  -> UI reads text locally and POSTs { documentText }
  -> HTTP adapter parses request DTO and authenticates actor
  -> ImportSavedFilter.import(actor, input, { signal })
  -> JSON.parse(documentText) => unknown
  -> parseSavedFilterDocument(unknown) => SavedFilterDocumentV1
  -> parseSavedFilterFilterDtoV1(dto.filter) => FilterDefinition
  -> collectReferencedFieldIds(filter)
  -> persistence transaction:
       - verify active, accessible fields through field catalog
       - reject missing/deleted/inaccessible IDs
       - create saved filter via existing creation path
       - store idempotency replay record when key exists
  -> protocol projection of created SavedFilter
  -> UI refreshes saved-filter list and confirms import
```

### Failure Flow

```txt
JSON.parse throws SyntaxError
  -> document codec catches and returns InvalidSavedFilterJson
  -> HTTP adapter returns 400 with stable error code

version is missing, non-numeric, or not 1
  -> document codec returns UnsupportedSavedFilterDocumentVersion
  -> HTTP adapter returns 422

valid v1 DTO contains an invalid filter AST or unknown keys
  -> document codec returns InvalidSavedFilterDocument
  -> HTTP adapter returns 400

referenced field is deleted, missing, or inaccessible at transaction time
  -> service returns DeletedFieldReference
  -> transaction rolls back, no filter is created
  -> HTTP adapter returns 422
```

### Retry / Cancellation / Idempotency Flow

- The request adapter passes its `AbortSignal` to import, transaction, and field lookup.
- Cancellation is classified before dependency failures and maps to the repository’s established cancellation response.
- Imports are mutating commands. If an `Idempotency-Key` is present, persist its document hash and resulting saved-filter ID in the same transaction as filter creation.
- A replay with the same key and document hash returns the original filter with `200 OK`.
- Reuse of a key with a different document hash returns the repository’s existing idempotency conflict error.
- Do not retry import automatically in the service. The client or transport may retry safely with the same idempotency key.

### Observability Flow

Record structured, safe telemetry at the HTTP/service boundary:

```ts
{
  operation: "importSavedFilter",
  documentVersion: 1,
  referencedFieldCount,
  outcome: "imported" | "replayed" | "rejected",
  errorTag,
}
```

Do not log document text, literal filter values, names, or arbitrary parser exceptions. Preserve existing request correlation and error-reporting hooks.

## Files to Add / Change / Delete

Exact paths are repository-dependent.

| Action | Proposed module | Ownership |
|---|---|---|
| Add | `saved-filter-document-v1.ts` | Versioned JSON DTO, strict parser, projections, error types. |
| Add | `import-saved-filter.ts` | Import orchestration service and narrow adapter dependency types. |
| Change | Existing saved-filter domain module | Expose canonical filter projection/reconstruction and referenced-field collection if absent. |
| Change | Existing saved-filter repository/adapter | Transactional creation and idempotency replay persistence, if no shared command-idempotency facility exists. |
| Change | Existing field catalog/repository adapter | Active-and-accessible field lookup for a set of IDs. |
| Change | Existing HTTP routes/controller | Export endpoint and import endpoint, typed-error mapping, attachment projection. |
| Change | Existing saved-filter UI | Export action, JSON file selection, user-facing import errors, list refresh. |
| Add | Adjacent domain/service/route tests | Behavior tests described below. |
| Delete | None | No replacement or removal is required. |

## RGR TDD Test Plan

### Slice 1: Export/import document codec

- **RED:** Given a canonical saved filter, when projected and parsed, then it round-trips to the same document semantics.
- **GREEN:** Add V1 projection and strict codec.
- **REFACTOR:** Extract only shared canonical filter projection logic already used by existing API paths.

Also prove rejection of malformed JSON, unknown version, unknown top-level keys, malformed clauses, invalid operators, and invalid value shapes.

### Slice 2: Deleted-field rejection

- **RED:** Given a valid V1 import referencing a deleted field, when imported through `ImportSavedFilter`, then it returns `DeletedFieldReference` and no record persists.
- **GREEN:** Add referenced-field collection and transactional active-field validation.
- **REFACTOR:** Keep field liveness policy in one service/domain operation.

### Slice 3: Successful import

- **RED:** Given an authorized actor and all active referenced fields, when importing a V1 document, then a new saved filter persists with equivalent filter semantics.
- **GREEN:** Add the creation orchestration through the existing saved-filter creation path.
- **REFACTOR:** Preserve existing naming and authorization behavior without duplicating it.

### Slice 4: HTTP and UI behavior

- **RED:** Given a selected valid JSON file, when the user imports it, then the saved-filter list includes the created filter; given each typed failure, then the user sees the mapped actionable error.
- **GREEN:** Add route/controller and UI wiring.
- **REFACTOR:** Reuse existing request, notification, and refresh patterns.

### Slice 5: Retry and race protection

- **RED:** Given a repeated import with the same idempotency key and document hash, when replayed, then one saved filter exists and the original result returns.
- **GREEN:** Add transactional replay storage.
- **REFACTOR:** Use an existing idempotency facility if present.

For a repository with a representative database test environment, add a concurrent test where field deletion races with import. Assert the transaction either imports only while the field remains active or rejects without creating a filter.

## Risks and Open Questions

1. **Canonical filter DTO:** Confirm the existing serialized filter AST and whether it already has a versioned codec. Reuse it rather than introducing a parallel representation.
2. **Deleted-field semantics:** This spec treats soft-deleted, missing, and inaccessible fields identically at the public boundary. Confirm whether any existing API intentionally exposes these distinctions.
3. **Filter value portability:** If values can include field references, saved entity IDs, relative dates, or user-specific values, their V1 encodings need explicit parser rules before implementation.
4. **Name collisions:** Reuse the existing create-saved-filter name policy. If none exists, reject collisions with `SavedFilterNameConflict`; do not silently rename imports.
5. **Export authorization:** Assume export requires the same permission as reading the saved filter.
6. **Idempotency infrastructure:** Use the repository’s established command-idempotency facility if present. Otherwise add the narrow persistence capability above.
7. **Transactional field validation:** Confirm the database isolation/locking mechanism needed to prevent deletion between validation and create.

**Deviations:** None.
