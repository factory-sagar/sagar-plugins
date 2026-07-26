# Saved Filter JSON Import and Export

## Summary

Add versioned JSON export and import for saved filters. Exports produce a portable document, imports strictly parse it, reject unknown versions and deleted field references, then persist a new saved filter only after validation succeeds.

## Context / Current State

No repository was provided or discoverable, so existing saved-filter types, storage, routes, UI, schema library, error representation, telemetry, and test conventions are unknown.

Current behavior is assumed to support persisted saved filters. This change adds import/export without changing existing filter execution semantics.

## Goals

- Export one saved filter as JSON.
- Import a previously exported filter.
- Reject malformed JSON.
- Reject unsupported document versions.
- Reject filters referencing deleted fields.
- Never partially persist an invalid import.

## Non-Goals

- Migrating legacy unversioned exports.
- Editing or merging existing saved filters during import.
- Restoring permissions, sharing, ownership, audit history, or IDs from an export.
- Importing multiple filters at once.
- Automatically repairing deleted field references.

## Invariants

- Export documents include an explicit version.
- Import treats file text and parsed JSON as untrusted boundary input.
- Only supported versions reach the service layer.
- Imported filters are persisted with a new saved-filter identity and the importing owner.
- A deleted field reference is an expected failure, not a silently removed clause.
- Invalid imports cause no persistence writes.
- Persisted saved-filter data is parsed before domain or service logic consumes it.

## Design Constraints

Standards applied: boundary parsing, precise typed failures, deep service modules, explicit persistence seams, protocol projections, real-seam testing, strict type contracts, and Red-Green-Refactor workflow.

Repository-dependent assumptions:

- The application has an authoritative field catalog capable of resolving active versus deleted fields.
- Saved filters have a canonical domain representation distinct from persistence and protocol DTOs.
- The selected import path already has authenticated ownership context.
- The saved-filter store can atomically revalidate referenced fields while creating the imported filter, or the equivalent transaction can be owned by an existing persistence layer.

## Alternatives Considered

### Option 1: Export raw persisted rows and import them directly

```ts
type Export = SavedFilterRow;
```

**Trade-offs**

- Lowest initial implementation cost.
- Leaks storage details, internal IDs, owner identity, and schema migrations into a public file format.
- Couples import compatibility to database representation.
- Makes strict versioning and safe validation difficult.
- Rejected because persistence records are not a portable public contract.

### Option 2: Versioned public document plus import service, recommended

```ts
type SavedFilterExportV1 = {
  readonly format: "saved-filter";
  readonly version: 1;
  readonly filter: SavedFilterExportFilterV1;
};
```

**Trade-offs**

- Establishes a stable, explicitly versioned boundary contract.
- Keeps import policy, deleted-field validation, and persistence orchestration local to one deep service module.
- Adds parser and projection code, but isolates future format versions.
- Recommended.

### Option 3: Client-side import validation with direct persistence request

```ts
parseImportInUi(fileText);
await api.createSavedFilter(parsedFilter);
```

**Trade-offs**

- Gives early feedback.
- Cannot enforce deleted-field validation or no-write guarantees against concurrent field deletion.
- Duplicates domain parsing and validation policy across clients.
- Rejected. The server-side service remains authoritative; the UI may only perform file selection and display projected results.

## Recommendation

Adopt **Option 2**. Define a versioned public export DTO, parse it strictly at the import boundary, convert it to canonical filter input, and create the imported filter through one service that verifies active fields and persists atomically.

## Proposed Design

### Domain Model and Types

Names and field shapes must be aligned with the repository’s existing saved-filter vocabulary.

```ts
type SavedFilterId = string & { readonly __brand: "SavedFilterId" };
type FieldId = string & { readonly __brand: "FieldId" };
type SavedFilterName = string & { readonly __brand: "SavedFilterName" };
type ImportedSavedFilterName = SavedFilterName;

type FilterClause =
  | {
      readonly kind: "comparison";
      readonly fieldId: FieldId;
      readonly operator: ComparisonOperator;
      readonly value: FilterValue;
    }
  | {
      readonly kind: "group";
      readonly operator: "and" | "or";
      readonly clauses: ReadonlyArray<FilterClause>;
    };

type SavedFilterDefinition = {
  readonly name: SavedFilterName;
  readonly clauses: ReadonlyArray<FilterClause>;
  readonly sort: ReadonlyArray<FilterSort>;
};

type SavedFilter = {
  readonly id: SavedFilterId;
  readonly ownerId: UserId;
  readonly definition: SavedFilterDefinition;
};
```

`SavedFilterDefinition` is canonical domain data. It must not include persistence IDs, ownership, timestamps, sharing state, or UI-only state.

### Types, Interfaces, and APIs

#### Public export contract

```ts
type SavedFilterExportV1 = {
  readonly format: "saved-filter";
  readonly version: 1;
  readonly filter: SavedFilterExportFilterV1;
};

type SavedFilterExportFilterV1 = {
  readonly name: string;
  readonly clauses: ReadonlyArray<FilterClauseDtoV1>;
  readonly sort: ReadonlyArray<FilterSortDtoV1>;
};

type SavedFilterExportDocument = SavedFilterExportV1;

type ExportSavedFilterError =
  | SavedFilterNotFound
  | SavedFilterAccessDenied;
```

The exact DTO shape must use the existing public filter syntax if one exists. Export must be an explicit protocol projection, not `{ ...savedFilter }`.

```ts
type ExportSavedFilter = {
  /**
   * Returns a portable, versioned document for a filter the caller may read.
   */
  export(
    input: Readonly<{
      readonly actor: AuthenticatedActor;
      readonly savedFilterId: SavedFilterId;
    }>,
  ): Promise<Result<SavedFilterExportDocument, ExportSavedFilterError>>;
};

function toSavedFilterExportV1(
  savedFilter: SavedFilter,
): SavedFilterExportV1;
```

The download adapter serializes the returned DTO with `JSON.stringify(document, null, 2)` and emits `application/json`.

#### Import boundary and service contracts

```ts
type ImportSavedFilter = {
  /**
   * Parses a versioned export and persists a new filter owned by the actor.
   */
  import(
    input: Readonly<{
      readonly actor: AuthenticatedActor;
      readonly fileText: string;
    }>,
  ): Promise<Result<SavedFilter, ImportSavedFilterError>>;
};

type ImportSavedFilterError =
  | MalformedSavedFilterImport
  | UnsupportedSavedFilterExportVersion
  | DeletedFieldReferenced
  | SavedFilterStoreUnavailable
  | SavedFilterCreateDenied;
```

```ts
type MalformedSavedFilterImport = {
  readonly _tag: "MalformedSavedFilterImport";
  readonly message: "Saved filter import is not valid JSON or does not match the supported document shape";
};

type UnsupportedSavedFilterExportVersion = {
  readonly _tag: "UnsupportedSavedFilterExportVersion";
  readonly version: number | undefined;
  readonly message: "Saved filter import uses an unsupported version";
};

type DeletedFieldReferenced = {
  readonly _tag: "DeletedFieldReferenced";
  readonly fieldId: FieldId;
  readonly message: "Saved filter references a deleted field";
};
```

```ts
function parseSavedFilterExport(
  fileText: string,
): Result<SavedFilterExportDocument, MalformedSavedFilterImport>;

function toImportSavedFilterInput(
  document: SavedFilterExportDocument,
): Result<
  Readonly<{ readonly definition: SavedFilterDefinition }>,
  MalformedSavedFilterImport | UnsupportedSavedFilterExportVersion
>;
```

The parser must:

1. Catch `JSON.parse` exceptions at the boundary.
2. Treat parsed output as `unknown`.
3. Strictly parse `format`, `version`, and all V1 fields.
4. Reject unknown object keys for this command-like document unless the established schema convention explicitly supports extensibility.
5. Return refined values, never cast decoded JSON to a domain type.

#### Persistence seam

```ts
type SavedFiltersForImport = {
  /**
   * Atomically verifies every referenced field remains active and creates the filter.
   */
  createImported(
    input: Readonly<{
      readonly ownerId: UserId;
      readonly definition: SavedFilterDefinition;
    }>,
  ): Promise<
    Result<
      SavedFilter,
      DeletedFieldReferenced | SavedFilterStoreUnavailable | SavedFilterCreateDenied
    >
  >;
};
```

The production adapter owns the transaction and must check active-field status during the create operation. This prevents a field-deletion race between service validation and persistence.

The service must depend only on `SavedFiltersForImport`, not raw database rows or a generic field repository.

### Seams, Boundaries, Adapters, and Implementations

| Layer | Owns | May know | Must not leak |
|---|---|---|---|
| Download protocol adapter | Download request, JSON serialization, content headers | Framework response APIs | Domain internals or persistence rows |
| `ExportSavedFilter` service | Read authorization and export use case | Narrow saved-filter lookup seam | HTTP or file APIs |
| Export projection | Domain-to-public V1 mapping | Canonical filter values | Persistence shape |
| Upload protocol adapter | File selection, text read, response projection | Browser/framework file APIs | Raw file text beyond parser boundary |
| `parseSavedFilterExport` | JSON and schema parsing | `unknown`, public DTO schema | Unrefined JSON |
| `ImportSavedFilter` service | Version dispatch, authorization, import orchestration | Parsed document and import seam | Framework or storage DTOs |
| `SavedFiltersForImport` adapter | Active-field check plus atomic persistence | Storage and transaction APIs | Raw rows to the service |
| Response projection | Success/error-to-UI or HTTP conversion | Typed result | Causes, request bodies, or unsafe diagnostics |

No new adapter should be added if an existing saved-filter persistence adapter can cohesively implement `createImported`.

## Call Stacks and Data Flow

### Current / Old Flow

```txt
saved filter domain value
  -> existing saved-filter persistence / UI behavior

No portable export or import behavior exists.
```

### Proposed / New Export Flow

```txt
user selects "Export"
  -> protocol adapter parses route/action input
  -> ExportSavedFilter.export(actor, savedFilterId)
  -> existing authorized saved-filter lookup seam
  -> SavedFilter domain value
  -> toSavedFilterExportV1(savedFilter)
  -> SavedFilterExportV1 DTO
  -> JSON.stringify DTO
  -> attachment/download response
```

### Proposed / New Import Flow

```txt
user selects export JSON file
  -> upload adapter reads text
  -> ImportSavedFilter.import({ actor, fileText })
  -> parseSavedFilterExport(fileText)
  -> SavedFilterExportDocument DTO
  -> version dispatch
  -> canonical SavedFilterDefinition
  -> SavedFiltersForImport.createImported({ ownerId, definition })
  -> transactional active-field verification
  -> persistence projection and create
  -> SavedFilter domain value
  -> protocol projection
  -> success response / refreshed saved-filter list
```

### Failure Flow

```txt
fileText
  -> JSON.parse throws
  -> MalformedSavedFilterImport
  -> protocol error projection
  -> user-visible import rejection, no write

unknown JSON document
  -> strict V1 parser rejects shape
  -> MalformedSavedFilterImport
  -> protocol error projection
  -> user-visible import rejection, no write

parsed document
  -> version dispatch rejects version
  -> UnsupportedSavedFilterExportVersion
  -> protocol error projection
  -> user-visible import rejection, no write

canonical definition
  -> transactional active-field check finds deleted FieldId
  -> DeletedFieldReferenced
  -> protocol error projection
  -> user-visible import rejection, no write

persistence exception
  -> storage adapter classifies unknown cause
  -> SavedFilterStoreUnavailable
  -> protocol error projection
```

### Retry / Cancellation / Idempotency Flow

- Import is not idempotent by default. Re-uploading a valid export creates another saved filter unless existing product behavior has a duplicate policy.
- Do not add automatic retries for import creation. A retry after an ambiguous storage failure can create duplicates.
- The protocol adapter should pass the caller-owned cancellation signal to file-reading and persistence APIs if the local framework supports it.
- Whether the database transaction is aborted on request cancellation is repository-dependent and must follow existing transaction conventions.

### Observability Flow

Use existing telemetry only. On success or failure, emit safe fields such as:

```ts
{
  operation: "importSavedFilter",
  outcome: "success" | "rejected" | "failed",
  errorTag?: ImportSavedFilterError["_tag"],
  exportVersion?: number,
}
```

Do not log imported file contents, clause values, arbitrary parser causes, or raw JSON. Add field IDs to telemetry only if current policy classifies them as safe identifiers.

## Files to Add / Change / Delete

Exact paths are open because no repository was supplied.

| Module responsibility | Expected change |
|---|---|
| Saved-filter domain module | Add or reuse canonical filter-definition construction and referenced-field traversal. |
| Saved-filter export DTO/projection module | Add V1 export document types and `toSavedFilterExportV1`. |
| Saved-filter import parser module | Add strict JSON parsing and V1 document refinement. |
| Saved-filter import service module | Add version dispatch and import orchestration. |
| Saved-filter persistence adapter | Add `createImported`, including transactional active-field verification and persistence projection. |
| Existing export endpoint/action | Add a download handler that calls the export service and projects JSON. |
| Existing import endpoint/action | Add upload handling that calls the import service and projects typed outcomes. |
| Saved-filter UI | Add export and import affordances only where saved filters are already managed. |
| Domain, parser, service, adapter, and protocol tests | Add behavior tests colocated according to repository convention. |
| Schema migration | None expected, unless current persistence cannot store the already-supported canonical filter definition. |

## RGR TDD Test Plan

Each slice begins with a failing behavior test through the indicated public seam, followed by the minimal implementation.

1. **Export V1**
   - **RED:** Export an authorized saved filter through the service or endpoint.
   - Assert the document has `format: "saved-filter"`, `version: 1`, and only portable filter data.
   - **GREEN:** Add the V1 projection and JSON download serialization.

2. **Valid import**
   - **RED:** Import a valid V1 JSON document through the import service with a real-seam recording store.
   - Assert a new filter is created for the importing actor, with canonical clauses and sort values.
   - **GREEN:** Add strict parsing, V1 dispatch, and `createImported` orchestration.

3. **Malformed JSON and malformed document**
   - **RED:** Import invalid JSON, an array, an incomplete V1 document, and a document with unknown command keys.
   - Assert `MalformedSavedFilterImport` and zero persistence writes.
   - **GREEN:** Implement parser rejection and protocol error projection.

4. **Unknown version**
   - **RED:** Import a structurally valid document with an unsupported version.
   - Assert `UnsupportedSavedFilterExportVersion` and zero persistence writes.
   - **GREEN:** Implement explicit version dispatch with no permissive fallback.

5. **Deleted field reference**
   - **RED:** Import a valid V1 document containing a deleted field.
   - Assert `DeletedFieldReferenced` and zero created filters.
   - **GREEN:** Add active-field verification in the import persistence operation.

6. **Race-safe persistence behavior**
   - **RED:** In a representative local persistence test, delete or mark a field inactive immediately before `createImported` commits.
   - Assert the create fails atomically with `DeletedFieldReferenced`.
   - **GREEN:** Add the transaction, lock, or conditional write that the repository’s storage technology requires.

7. **Protocol/UI integration**
   - **RED:** Exercise export download and import upload through the user-facing protocol seam.
   - Assert valid imports appear in the saved-filter list; typed failures display the established error presentation; invalid imports do not refresh or alter the list.
   - **GREEN:** Wire handlers and UI controls to the services.

8. **Regression evidence**
   - Run the repository’s targeted tests after every slice.
   - Run the canonical type check, lint, full test suite, and changed-code coverage gate at completion.
   - Target at least 80% line and branch coverage for changed code, subject to the repository’s actual configured coverage tooling.

Tests must use real seams, such as injected recording stores or representative local persistence. Do not use module mocks or method spies.

## Risks and Open Questions

1. **Export schema:** Does an existing public filter DTO already exist? Reuse it only if it is explicitly versionable and does not expose persistence or owner data.
2. **Filter values:** Which clause value types are legal, and do any require additional JSON codecs, such as dates, relative periods, or typed IDs?
3. **Deleted field semantics:** Does “deleted” include archived, hidden, permission-revoked, or merely unavailable fields? This determines the authoritative active-field predicate.
4. **Field references:** Are field references present only in clauses, or also in sort, grouping, formulas, display settings, and nested saved-filter references?
5. **Authorization:** May an importer use fields they cannot currently access? The recommended default is rejection via the existing field-access policy.
6. **Naming collisions:** Should imported filters retain the exported name, be auto-suffixed, or require a user-provided name? No behavior is specified, so preserve the project’s existing create-filter naming policy.
7. **Error transport:** The concrete HTTP status codes, RPC error codes, UI copy, and schema library must follow repository conventions.
8. **Persistence atomicity:** The storage implementation must determine the correct transaction or conditional-write strategy for simultaneous field deletion and import.

Deviations: none.
