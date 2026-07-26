# Saved Filter JSON Import and Export

## Summary

Add versioned JSON export and import for saved filters. Imports validate JSON and the portable filter definition before persisting, rejecting malformed JSON, unsupported versions, and references to deleted fields.

## Context / Current State

No repository was supplied. This spec uses logical module names and treats current saved-filter APIs, authorization, persistence, schema, telemetry, and test conventions as repository-dependent assumptions.

## Goals

- Export one saved filter as portable, versioned JSON.
- Import one exported JSON document as a new saved filter.
- Reject malformed JSON.
- Reject unknown format versions.
- Reject filters referencing fields that no longer exist.
- Preserve existing saved-filter access control.

## Non-Goals

- Bulk import/export.
- Updating an existing saved filter during import.
- Migrating unsupported historical formats.
- Importing executable code, arbitrary metadata, ownership, sharing, usage statistics, or audit history.
- Cross-product field mapping.

## Invariants

- Only canonical, portable filter definition data crosses the export boundary.
- Imported text is `unknown` until JSON parsing and format parsing succeed.
- Imported field references must resolve against currently active fields before persistence.
- Expected failures are typed values, not thrown control flow.
- A successful import creates exactly one new filter and never overwrites another.
- Export and import preserve semantic filter meaning, not identity or ownership.

## Design Constraints

Standards applied: `DESIGNING_MODULES`, `BOUNDARIES_AND_PARSING`, `ERROR_HANDLING`, `OBSERVABILITY`, `TESTING_AND_VERIFICATION`, `TYPE_CONTRACTS`, `ASYNC_AND_WORKFLOWS`, and the RGR TDD workflow.

- Reuse the repository’s existing saved-filter parser, persistence adapter, authorization mechanism, schema library, `Result` shape, and telemetry path.
- Treat stored filter definitions and imported JSON as separate untrusted boundaries.
- Use strict parsing for the import envelope and all nested command objects.
- Maintain caller-owned cancellation for all I/O.
- The create operation must have an idempotency policy if the existing import endpoint is retryable.

## Alternatives Considered

### Option 1: Export and import raw persistence records

Export the database row and reinsert it on import.

**Rejected:** leaks persistence schema, identity, owner, timestamps, and internal fields. It also couples portability to storage and cannot safely distinguish deleted fields from stale records.

### Option 2: Export the existing public saved-filter response DTO

Reuse the API response as the import payload.

**Rejected:** public response DTOs often include server-managed fields and display-only projections. Combining protocol response and import command shapes creates an accidental interface and weakens strict parsing.

### Option 3: Versioned portable-definition envelope, recommended

Define a dedicated JSON envelope whose `filter` member is a portable definition, parse it at import, validate field references through an existing-field lookup seam, then create a new saved filter.

**Selected:** separates protocol, domain, and persistence representations; makes version dispatch explicit; and confines evolution to one codec.

## Recommendation

Use **Option 3**. Add a `SavedFilterTransfer` boundary module that owns v1 encoding and decoding. Reuse the existing domain module to validate filter semantics, the existing field catalog to resolve field references, and the existing saved-filter store to create the new resource.

## Proposed Design

### Domain Model and Types

```ts
declare const savedFilterIdBrand: unique symbol;
declare const fieldIdBrand: unique symbol;

type SavedFilterId = string & {
  readonly [savedFilterIdBrand]: "SavedFilterId";
};

type FieldId = string & {
  readonly [fieldIdBrand]: "FieldId";
};

type SavedFilterActor = /* existing authenticated principal type */ unknown;

type PortableFilterDefinitionV1 = {
  readonly name: string;
  readonly query: /* existing canonical saved-filter query */ unknown;
};

type SavedFilterTransferV1 = {
  readonly format: "saved-filter";
  readonly version: 1;
  readonly filter: PortableFilterDefinitionV1;
};

type ParsedSavedFilterTransfer =
  | {
      readonly version: 1;
      readonly definition: PortableFilterDefinitionV1;
    };
```

`PortableFilterDefinitionV1` must contain only values required to recreate the filter’s behavior. The repository’s existing canonical filter definition owns the concrete query structure. It must exclude:

- saved-filter ID;
- owner and sharing state;
- creation/update timestamps;
- audit data;
- persistence-only columns;
- server-calculated display data.

### Types, Interfaces, and APIs

```ts
type ExportSavedFilterInput = {
  readonly actor: SavedFilterActor;
  readonly savedFilterId: SavedFilterId;
};

type ImportSavedFilterInput = {
  readonly actor: SavedFilterActor;
  readonly json: string;
  readonly idempotencyKey?: string;
};

type ImportSavedFilterSuccess = {
  readonly savedFilterId: SavedFilterId;
  readonly name: string;
};

type ImportSavedFilterError =
  | SavedFilterImportMalformedJson
  | SavedFilterImportInvalidDocument
  | SavedFilterImportUnsupportedVersion
  | SavedFilterImportDeletedFieldReference
  | SavedFilterImportUnauthorized
  | SavedFilterStoreUnavailable;

type SavedFiltersForTransfer = {
  findReadable(
    input: ExportSavedFilterInput,
    options?: { readonly signal?: AbortSignal },
  ): Promise<Result<SavedFilter, SavedFilterNotFound | SavedFilterAccessDenied | SavedFilterStoreUnavailable>>;

  createImported(
    input: {
      readonly actor: SavedFilterActor;
      readonly definition: PortableFilterDefinitionV1;
      readonly idempotencyKey?: string;
    },
    options?: { readonly signal?: AbortSignal },
  ): Promise<Result<ImportSavedFilterSuccess, SavedFilterAccessDenied | SavedFilterStoreUnavailable>>;
};

type ActiveFieldsForTransfer = {
  findMissing(
    fieldIds: ReadonlySet<FieldId>,
    options?: { readonly signal?: AbortSignal },
  ): Promise<Result<ReadonlySet<FieldId>, FieldCatalogUnavailable>>;
};

type SavedFilterTransferService = {
  export(
    input: ExportSavedFilterInput,
    options?: { readonly signal?: AbortSignal },
  ): Promise<Result<SavedFilterTransferV1, SavedFilterNotFound | SavedFilterAccessDenied | SavedFilterStoreUnavailable>>;

  import(
    input: ImportSavedFilterInput,
    options?: { readonly signal?: AbortSignal },
  ): Promise<Result<ImportSavedFilterSuccess, ImportSavedFilterError>>;
};
```

```ts
type SavedFilterTransferCodec = {
  encodeV1(filter: SavedFilter): SavedFilterTransferV1;

  parse(
    raw: unknown,
  ): Result<
    ParsedSavedFilterTransfer,
    | SavedFilterImportInvalidDocument
    | SavedFilterImportUnsupportedVersion
  >;
};
```

Expected failure tags:

```ts
type SavedFilterImportMalformedJson = {
  readonly _tag: "SavedFilterImportMalformedJson";
};

type SavedFilterImportInvalidDocument = {
  readonly _tag: "SavedFilterImportInvalidDocument";
  readonly reason: "invalid-envelope" | "invalid-filter-definition";
};

type SavedFilterImportUnsupportedVersion = {
  readonly _tag: "SavedFilterImportUnsupportedVersion";
  readonly version: number | string | undefined;
};

type SavedFilterImportDeletedFieldReference = {
  readonly _tag: "SavedFilterImportDeletedFieldReference";
  readonly missingFieldIds: ReadonlyArray<FieldId>;
};
```

The transport adapter maps these failures to the repository’s established protocol errors. At minimum, malformed JSON, invalid documents, unsupported versions, and deleted-field references must be distinguishable to the caller.

### Seams, Boundaries, Adapters, and Implementations

| Owner | Responsibility | Must not know |
|---|---|---|
| Inbound API/UI adapter | Authenticate, parse route/request envelope, serialize download or response | filter query internals, persistence |
| `SavedFilterTransferService` | Coordinate export/import policy, authorization inputs, field validation, persistence calls | HTTP/framework request shapes |
| `SavedFilterTransferCodec` | Strictly encode v1 and parse/version-dispatch imported documents | users, storage, HTTP |
| Existing saved-filter domain module | Validate canonical filter rules and collect referenced `FieldId`s | JSON, storage rows |
| `ActiveFieldsForTransfer` adapter | Resolve whether referenced fields remain active | transfer-envelope rules |
| Existing saved-filter persistence adapter | Read readable filters and create imported filters | raw import JSON |

The codec is the sole version seam. Future versions extend `parse` with an explicit version case, never by permissive fallback.

## Call Stacks and Data Flow

### Current / Old Flow

```txt
saved-filter UI/API
  -> existing saved-filter read or create handler
  -> existing service
  -> persistence adapter
  -> saved-filter response DTO
```

There is no portable transfer contract.

### Proposed / New Flow: Export

```txt
authenticated export request
  -> inbound adapter parses savedFilterId
  -> ExportSavedFilterInput
  -> SavedFilterTransferService.export
  -> SavedFiltersForTransfer.findReadable
  -> SavedFilter domain value
  -> SavedFilterTransferCodec.encodeV1
  -> SavedFilterTransferV1
  -> JSON.stringify at protocol boundary
  -> attachment/download response
```

`JSON.stringify` operates only on the codec-produced DTO. The adapter sets the repository-standard JSON content type and a safe filename derived from an approved display name or existing naming helper.

### Proposed / New Flow: Import

```txt
authenticated import request
  -> inbound adapter parses request container
  -> raw JSON text
  -> JSON.parse inside import boundary
  -> unknown
  -> SavedFilterTransferCodec.parse
  -> ParsedSavedFilterTransfer
  -> existing domain parser reconstructs canonical definition
  -> collectReferencedFieldIds(definition)
  -> ActiveFieldsForTransfer.findMissing
  -> no missing fields
  -> SavedFiltersForTransfer.createImported
  -> ImportSavedFilterSuccess
  -> protocol projection
```

### Failure Flow

```txt
JSON.parse throws SyntaxError
  -> boundary catches and classifies
  -> SavedFilterImportMalformedJson
  -> protocol error response

codec rejects envelope / nested definition
  -> SavedFilterImportInvalidDocument
  -> protocol error response

codec sees unsupported version
  -> SavedFilterImportUnsupportedVersion
  -> protocol error response

field lookup returns missing IDs
  -> SavedFilterImportDeletedFieldReference
  -> no write
  -> protocol error response

store / field catalog dependency failure
  -> adapter classifies unknown cause
  -> typed dependency error
  -> existing error-reporting path
```

No raw JSON, parsed query values, or caught causes are included in returned errors or telemetry.

### Retry / Cancellation / Idempotency Flow

```txt
request AbortSignal
  -> transfer service
  -> field catalog lookup and saved-filter store calls
```

- The service must pass the caller signal downstream.
- Import has no retries or background work.
- If the existing import endpoint can be retried, use its established idempotency mechanism. The same idempotency key must replay the original successful import instead of creating another filter.
- If no retryable command infrastructure exists, document import as non-retryable before exposing it through a retrying transport.

### Observability Flow

Use the existing telemetry path at the inbound adapter and service boundary. Emit only safe fields:

```ts
{
  operation: "importSavedFilter",
  transferVersion: 1,
  errorTag: result.error._tag,
  missingFieldCount: result.error._tag === "SavedFilterImportDeletedFieldReference"
    ? result.error.missingFieldIds.length
    : undefined,
}
```

Do not log JSON text, complete filter definitions, or raw caught errors.

## Files to Add / Change / Delete

Exact paths are open until repository inspection. Map these responsibilities to the closest established modules:

| Logical module | Change | Responsibility |
|---|---|---|
| `saved-filters/transfer.ts` | Add | v1 envelope types, strict parser, encoder, transfer errors |
| `saved-filters/transfer-service.ts` | Add or extend existing service | Export/import orchestration and narrow dependency interfaces |
| `saved-filters/domain.ts` | Change if absent | Canonical definition parser and `collectReferencedFieldIds` |
| `saved-filters/http.ts` or route/controller | Change | Import/export entrypoints and protocol projections |
| `saved-filters/store.ts` | Change if needed | Readable lookup and imported create operation |
| `fields/catalog.ts` | Change only if no existing capability | `findMissing` implementation over active fields |
| transfer codec tests | Add | Strict decoding/version behavior |
| transfer service tests | Add | Field validation, persistence, error propagation |
| endpoint/integration tests | Add | User-visible export/import behavior |

No migrations are required unless the existing idempotency policy needs durable replay records.

## RGR TDD Test Plan

### Slice 1: Export v1

**RED:** Through the export service interface, a readable saved filter produces a v1 portable envelope containing only canonical portable definition data.

**GREEN:** Add `encodeV1` and service wiring.

**REFACTOR:** Extract projection helpers only if the existing domain model makes portable selection non-obvious.

### Slice 2: Import accepted v1 document

**RED:** Importing exported v1 JSON creates one new filter with equivalent canonical definition and current actor ownership. Assert observable store records through a recording adapter or representative database seam.

**GREEN:** Parse, reconstruct, and persist the definition.

**REFACTOR:** Keep protocol projection separate from persistence projection.

### Slice 3: Malformed and invalid JSON

**RED:** Invalid JSON text returns `SavedFilterImportMalformedJson`; valid JSON with invalid envelope or nested definition returns `SavedFilterImportInvalidDocument`; neither writes a filter.

**GREEN:** Add JSON parse classification and strict codec parsing.

### Slice 4: Unknown version

**RED:** A structurally valid envelope with an unsupported version returns `SavedFilterImportUnsupportedVersion`; no field lookup or write occurs.

**GREEN:** Add explicit version dispatch.

### Slice 5: Deleted field references

**RED:** A valid v1 definition referencing one or more inactive/deleted field IDs returns `SavedFilterImportDeletedFieldReference`, reports only the missing IDs according to existing disclosure policy, and performs no write.

**GREEN:** Add reference collection and `ActiveFieldsForTransfer.findMissing` check.

### Slice 6: Access, dependency, and cancellation behavior

**RED:** Export access denial, import authorization denial, field-catalog failure, store failure, and request cancellation preserve typed outcomes and produce no partial write.

**GREEN:** Propagate existing authorization, typed failure, and cancellation contracts.

### Cross-cutting verification

- Codec behavior tests: v1 round trip preserves semantic definition, rejects unknown keys, rejects non-object/null/array inputs, and rejects unknown versions.
- Adapter contract test: field catalog distinguishes active from deleted fields using the real persistence seam when deletion semantics depend on database state.
- Endpoint/integration test: export download followed by import returns a new saved-filter identity with equivalent behavior.
- Run the repository’s canonical formatter, lint, typecheck, targeted tests, and full test suite after implementation.

## Risks and Open Questions

1. **Canonical filter representation:** Confirm which existing domain value is the portable source of truth and whether its current parser rejects all stale/deleted references.
2. **Deleted-field semantics:** Confirm whether “deleted” means physically absent, soft-deleted, inactive, inaccessible to the importing actor, or all of these. The field lookup must match that product definition.
3. **Name collisions:** This spec preserves the imported name. If names must be unique per owner/scope, reuse the existing create policy and expose its typed conflict failure.
4. **Authorization scope:** Confirm whether export/import must be restricted by workspace, project, or ownership, then pass the existing typed principal into the service.
5. **Idempotency:** Confirm whether the transport retries import requests. If yes, persistence must provide a durable replay mechanism.
6. **External query values:** If filter values can contain sensitive data, confirm whether export is allowed to include them. This spec assumes portability requires them and that existing authorization already permits viewing them.
7. **Version evolution:** Version `1` is the initial supported version. Unknown versions must never be coerced into v1.

**Deviations: none.**
