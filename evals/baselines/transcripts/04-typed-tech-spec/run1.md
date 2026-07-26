# Saved Filter JSON Import and Export

## Summary

Add a versioned, portable saved-filter JSON document. Export serializes an authorized saved filter as version `1`; import parses and validates the document before saving it. Imports reject malformed JSON, unsupported versions, and every reference to a non-active field, including deleted fields.

## Context / Current State

No repository was provided. This specification assumes saved filters already have:

- An authenticated owner or actor context.
- A canonical in-memory filter definition.
- A persistence path for creating and reading saved filters.
- A field catalog or schema capable of determining which fields are currently active for a filter scope.

Repository-specific routes, source paths, error conventions, schema library, persistence implementation, and exact filter-AST shape remain assumptions to resolve during implementation.

## Goals

- Export an authorized saved filter as a downloadable JSON document.
- Import a JSON document as a new saved filter through the existing creation path.
- Reject:
  - malformed JSON;
  - structurally invalid version-1 documents;
  - any unsupported `version`;
  - filters referencing fields that are no longer active, including deleted fields.
- Keep parsing, field validation, authorization, persistence, and protocol serialization at separate boundaries.

## Non-Goals

- Cross-version migrations or automatic upgrades.
- Editing an existing saved filter through import.
- Recovering deleted fields.
- Supporting non-JSON formats.
- Adding arbitrary import/export of unrelated user data.

## Invariants

1. Only `format: "saved-filter"` documents with `version: 1` are accepted.
2. Unknown versions are rejected before version-specific document parsing.
3. Raw JSON, decoded JSON, storage rows, and HTTP/file payloads never enter domain or service logic unparsed.
4. Every field-bearing location in a filter definition is checked against the current active field catalog before persistence.
5. A rejected import creates no saved-filter record or idempotency receipt representing success.
6. Export omits persistence identity and ownership metadata, such as database IDs, owner IDs, timestamps, and audit fields.
7. The import document and filter literal values are never logged, traced, or included in error summaries.

## Design Constraints

Standards applied: `BOUNDARIES_AND_PARSING.md`, `DESIGNING_MODULES.md`, `ERROR_HANDLING.md`, `OBSERVABILITY.md`, `ASYNC_AND_WORKFLOWS.md`, `TESTING_AND_VERIFICATION.md`, `TYPE_CONTRACTS.md`, and `tdd-workflow`.

- Use the repository's established schema parser and typed-result convention.
- Version dispatch must use a permissive header parse followed by a strict version-1 parse.
- Mutating import requests reject unknown version-1 object fields.
- Expected failures use precise tagged result unions.
- The import create operation must use the existing idempotency mechanism, or introduce a scoped import receipt if none exists.

## Alternatives Considered

### Option 1: Client-only JSON parsing and direct save

The browser parses JSON, checks fields from its currently loaded UI metadata, then calls the existing create endpoint.

**Trade-offs**

- Low initial server work.
- Trusts stale client field metadata.
- Lets non-browser callers bypass validation.
- Cannot reliably protect persistence from malformed or deleted field references.

**Rejected:** validation must be enforced at the server-side application boundary.

### Option 2: Export and re-import opaque persistence rows

Export the database row or existing storage JSON, then restore it on import.

**Trade-offs**

- Minimal translation code.
- Couples the file format to storage schema and migrations.
- Risks exporting ownership, audit, database, or deleted-field state.
- Makes safe versioning difficult.

**Rejected:** persistence DTOs are not portable domain documents.

### Option 3: Versioned portable document with server-owned validation

Export projects a canonical saved filter into a portable versioned DTO. Import parses, validates active fields, converts to the canonical domain value, then uses the existing create path.

**Trade-offs**

- Explicit compatibility contract and failure behavior.
- Keeps field validity close to current authoritative schema.
- Requires a codec and field-catalog seam.

**Recommended.**

## Recommendation

Implement a shared `SavedFilterPortableV1` codec in the saved-filter domain area, plus application services for export and import. The codec owns document structure and structural filter parsing; the import service owns authorization, active-field resolution, domain binding, idempotency, and persistence sequencing.

## Proposed Design

### Domain Model and Types

```ts
type Result<T, E> =
  | { readonly _tag: "ok"; readonly value: T }
  | { readonly _tag: "err"; readonly error: E };

type SavedFilterId = string & { readonly __brand: "SavedFilterId" };
type FieldReference = string & { readonly __brand: "FieldReference" };
type ImportRequestId = string & { readonly __brand: "ImportRequestId" };

/** Existing parsed actor or principal type. */
type SavedFilterActor = ExistingSavedFilterActor;

/** Existing scope identifying the saved filter's list, object, or resource context. */
type SavedFilterScope = ExistingSavedFilterScope;

/** Existing canonical filter value with valid, bound field definitions. */
type SavedFilterDefinition = ExistingSavedFilterDefinition;

/**
 * A structurally valid filter whose field references have not yet been resolved
 * against the destination's current active field catalog.
 */
type UnboundSavedFilterDefinition = ExistingUnboundSavedFilterDefinition;

type SavedFilterPortableV1 = Readonly<{
  readonly format: "saved-filter";
  readonly version: 1;
  readonly filter: Readonly<{
    readonly name: string;
    readonly definition: PortableSavedFilterDefinitionV1;
    // Include a portable scope discriminator only if the existing domain requires one.
  }>;
}>;

/**
 * An explicit, JSON-safe projection of the existing filter AST or criteria model.
 *
 * This must contain every current field-bearing construct, including condition,
 * sort, grouping, aggregation, display, or other field-reference nodes that
 * exist in the repository's saved-filter model.
 */
type PortableSavedFilterDefinitionV1 = ExistingPortableFilterDefinitionV1;
```

The actual AST DTO must be derived from the existing canonical filter definition. It must not be a storage row or a cast of decoded JSON.

```ts
type MalformedSavedFilterJson = Readonly<{
  readonly _tag: "MalformedSavedFilterJson";
}>;

type InvalidSavedFilterDocument = Readonly<{
  readonly _tag: "InvalidSavedFilterDocument";
  readonly reason:
    | "invalid-envelope"
    | "invalid-v1-shape"
    | "unknown-v1-field"
    | "invalid-filter-definition";
}>;

type UnknownSavedFilterVersion = Readonly<{
  readonly _tag: "UnknownSavedFilterVersion";
  readonly receivedVersion: number;
}>;

type DeletedFieldReferences = Readonly<{
  readonly _tag: "DeletedFieldReferences";
  readonly fieldIds: ReadonlyArray<FieldReference>;
}>;

type IncompatibleSavedFilterScope = Readonly<{
  readonly _tag: "IncompatibleSavedFilterScope";
}>;

type ImportCancelled = Readonly<{
  readonly _tag: "ImportCancelled";
}>;

type SavedFilterImportError =
  | MalformedSavedFilterJson
  | InvalidSavedFilterDocument
  | UnknownSavedFilterVersion
  | DeletedFieldReferences
  | IncompatibleSavedFilterScope
  | ImportCancelled
  | ExistingAuthorizationError
  | ExistingFieldCatalogError
  | ExistingSavedFilterPersistenceError;
```

### Types, Interfaces, and APIs

```ts
/**
 * Parses raw JSON text into a structurally valid, unbound version-1 document.
 * Unknown versions are identified before strict version-1 parsing.
 */
function parseSavedFilterPortableDocument(
  text: string,
): Result<
  Readonly<{
    readonly name: string;
    readonly definition: UnboundSavedFilterDefinition;
    readonly declaredScope?: SavedFilterScope;
  }>,
  MalformedSavedFilterJson | InvalidSavedFilterDocument | UnknownSavedFilterVersion
>;

/** Returns every field reference found anywhere in the parsed definition. */
function collectReferencedFields(
  definition: UnboundSavedFilterDefinition,
): ReadonlySet<FieldReference>;

/**
 * Binds field references to current active fields and performs any field-type,
 * operator, and value compatibility checks required by the existing filter model.
 */
function bindActiveFields(
  definition: UnboundSavedFilterDefinition,
  activeFields: ActiveFilterFields,
): Result<SavedFilterDefinition, InvalidSavedFilterDocument>;

interface ActiveFilterFieldCatalog {
  findActive(
    input: Readonly<{
      readonly actor: SavedFilterActor;
      readonly scope: SavedFilterScope;
      readonly fieldIds: ReadonlySet<FieldReference>;
    }>,
    options?: Readonly<{ readonly signal?: AbortSignal }>,
  ): Promise<Result<ActiveFilterFields, ExistingFieldCatalogError>>;
}

interface SavedFiltersForImport {
  createImported(
    input: Readonly<{
      readonly actor: SavedFilterActor;
      readonly scope: SavedFilterScope;
      readonly name: string;
      readonly definition: SavedFilterDefinition;
      readonly importRequestId: ImportRequestId;
    }>,
    options?: Readonly<{ readonly signal?: AbortSignal }>,
  ): Promise<Result<ExistingSavedFilter, ExistingSavedFilterPersistenceError>>;
}

interface SavedFiltersForExport {
  findAuthorized(
    input: Readonly<{
      readonly actor: SavedFilterActor;
      readonly savedFilterId: SavedFilterId;
    }>,
    options?: Readonly<{ readonly signal?: AbortSignal }>,
  ): Promise<
    Result<
      ExistingSavedFilter,
      ExistingSavedFilterNotFound | ExistingAuthorizationError | ExistingSavedFilterPersistenceError
    >
  >;
}
```

```ts
type ImportSavedFilterRequest = Readonly<{
  readonly actor: SavedFilterActor;
  readonly targetScope: SavedFilterScope;
  readonly documentText: string;
  readonly importRequestId: ImportRequestId;
}>;

interface ImportSavedFilter {
  import(
    request: ImportSavedFilterRequest,
    options?: Readonly<{ readonly signal?: AbortSignal }>,
  ): Promise<Result<ExistingSavedFilter, SavedFilterImportError>>;
}

interface ExportSavedFilter {
  export(
    request: Readonly<{
      readonly actor: SavedFilterActor;
      readonly savedFilterId: SavedFilterId;
    }>,
    options?: Readonly<{ readonly signal?: AbortSignal }>,
  ): Promise<
    Result<
      SavedFilterPortableV1,
      ExistingSavedFilterNotFound | ExistingAuthorizationError | ExistingSavedFilterPersistenceError
    >
  >;
}
```

### Seams, Boundaries, Adapters, and Implementations

| Owner | Responsibility |
|---|---|
| Saved-filter portable codec | Version header parsing, strict V1 parsing, projection, field-reference collection, domain binding. Pure, no I/O. |
| Import service | Sequences parsing, scope compatibility, active-field lookup, binding, idempotent create, and typed failures. |
| Export service | Reads an authorized canonical saved filter and projects it into `SavedFilterPortableV1`. |
| Field-catalog adapter | Translates the repository's schema, metadata store, or field registry into `ActiveFilterFields`. It must exclude deleted fields. |
| Saved-filter repository adapter | Reads and persists canonical saved filters. Storage rows are parsed at this boundary. |
| HTTP/server-action adapter | Authenticates, bounds uploaded file size, reads text, invokes services, and projects typed results to existing protocol errors. |
| UI adapter | Starts download from an export response and sends selected file text plus a stable import request ID. It performs no authoritative validation. |

The core import service must not know about browser `File`, HTTP requests, multipart forms, ORM rows, or raw database errors.

## Call Stacks and Data Flow

### Current / Old Flow

The exact saved-filter create/read flow is repository-dependent. Before implementation, identify:

```txt
saved-filter UI or protocol entrypoint
  -> authorization convention
  -> existing saved-filter service or repository
  -> persistence adapter
  -> storage
```

The new feature must reuse this authorized canonical path rather than duplicate persistence behavior.

### Proposed / New Flow: Export

```txt
export control or GET export entrypoint
  -> authenticate and parse SavedFilterId
  -> ExportSavedFilter.export(actor, savedFilterId)
  -> SavedFiltersForExport.findAuthorized(...)
  -> canonical ExistingSavedFilter
  -> toSavedFilterPortableV1(savedFilter)
  -> SavedFilterPortableV1
  -> protocol projection: JSON.stringify(document)
  -> application/json download named by the existing safe filename convention
```

### Proposed / New Flow: Import

```txt
file selection or import request
  -> enforce existing import/body-size limit
  -> decode file as UTF-8 text
  -> authenticate and parse target scope + ImportRequestId
  -> ImportSavedFilter.import(...)
  -> JSON.parse(text) as unknown
  -> parse envelope header: format + numeric version
  -> version === 1 dispatch
  -> strict V1 parser
  -> UnboundSavedFilterDefinition
  -> collectReferencedFields(definition)
  -> ActiveFilterFieldCatalog.findActive(actor, targetScope, fieldIds)
  -> reject every absent or inactive field reference
  -> bindActiveFields(definition, activeFields)
  -> SavedFilterDefinition
  -> SavedFiltersForImport.createImported(...)
  -> imported canonical saved filter
  -> protocol projection
```

### Failure Flow

```txt
invalid UTF-8 or JSON syntax
  -> MalformedSavedFilterJson
  -> existing client-facing invalid-import response

valid JSON, missing or malformed envelope
  -> InvalidSavedFilterDocument { reason: "invalid-envelope" }

valid header, version !== 1
  -> UnknownSavedFilterVersion

version 1, unknown or malformed V1 fields
  -> InvalidSavedFilterDocument

valid V1 AST, any referenced field absent from active catalog
  -> DeletedFieldReferences
  -> no bind, no persistence call

valid active fields, invalid operator or value for resolved field type
  -> InvalidSavedFilterDocument { reason: "invalid-filter-definition" }

authorization, catalog, or persistence dependency failure
  -> existing typed dependency or authorization failure
  -> existing protocol error translation
```

The active-field check must cover all field references, not only primary filter predicates.

### Retry / Cancellation / Idempotency Flow

```txt
import request with ImportRequestId
  -> validate document and active fields
  -> transactionally create saved filter plus import receipt
  -> return original created result for a repeated ImportRequestId
```

- Reuse the repository's existing mutation idempotency facility if present.
- Otherwise, make `(actor or owner scope, importRequestId)` unique and persist the created saved-filter identity atomically with creation.
- Do not use a document hash alone as the idempotency key, because two intentional imports of the same file must remain distinguishable.
- Propagate a caller-owned `AbortSignal` to file/network, catalog, and repository operations where supported.
- A cancellation before persistence returns `ImportCancelled`.
- If cancellation occurs after a committed create but before the response, retrying the same request ID must replay the original result.
- Export has no mutating side effect and requires no retry mechanism.

### Observability Flow

```txt
entrypoint correlation context
  -> import/export service outcome
  -> existing telemetry mechanism
```

Emit only safe fields:

```ts
{
  operation: "importSavedFilter" | "exportSavedFilter",
  scopeKind: safeScopeKind,
  savedFilterId: safeSavedFilterId,
  importedVersion: 1,
  referencedFieldCount: number,
  rejectedFieldCount: number,
  errorTag: SavedFilterImportError["_tag"],
}
```

Never emit raw document text, filter values, file contents, names, arbitrary parse errors, or unclassified thrown causes.

## Files to Add / Change / Delete

Actual paths must follow repository layout. The following are logical owners.

| Logical module | Change |
|---|---|
| `saved-filters/domain/saved-filter-portable-v1.ts` | Add `SavedFilterPortableV1`, header parser, strict V1 parser, export projection, structural definition parser, and field-reference collector. |
| Existing saved-filter domain module | Add or reuse `bindActiveFields` and the canonical-to-portable definition projection. |
| `saved-filters/application/import-saved-filter.ts` | Add import orchestration and precise failure union. |
| `saved-filters/application/export-saved-filter.ts` | Add authorized export orchestration. |
| Existing field-schema adapter | Add a batched active-field lookup for an actor and saved-filter scope. |
| Existing saved-filter repository adapter | Add idempotent imported-create support only if existing create semantics do not provide it. |
| Existing import/export route, server action, or controller | Add raw document intake, typed response projection, JSON download response, and size-limit enforcement. |
| Existing UI saved-filter controls | Add export and import actions using existing download/file-picker conventions. |
| Existing migration directory, if needed | Add import-receipt uniqueness storage only when no established idempotency store exists. |
| Corresponding domain, application, adapter, protocol, and UI test files | Add behavior tests below. |

No existing files should be deleted.

## RGR TDD Test Plan

### Slice 1: Exported portable document

**Given** an authorized saved filter, **when** export is requested, **then** the result is a V1 document containing the canonical portable definition and no persistence identity metadata.

- **RED:** Behavior test through `ExportSavedFilter`.
- **GREEN:** Add canonical-to-V1 projection.
- **REFACTOR:** Centralize projection with the portable codec.

### Slice 2: Malformed JSON

**Given** an import document with invalid JSON syntax, **when** imported, **then** it returns `MalformedSavedFilterJson` and creates no filter.

- Supply a recording repository through the real persistence seam.
- Assert the repository contains no created filter, not internal method calls.

### Slice 3: Unknown version dispatch

**Given** valid JSON with `format: "saved-filter"` and `version: 2`, **when** imported, **then** it returns `UnknownSavedFilterVersion`, even when the document also contains V2-only fields.

This proves header parsing occurs before strict V1 parsing.

### Slice 4: Strict V1 parsing

**Given** a V1 document with malformed filter shape or unknown V1 properties, **when** imported, **then** it returns `InvalidSavedFilterDocument` and performs no persistence.

### Slice 5: Deleted-field rejection

**Given** a structurally valid V1 filter referencing a field absent from `ActiveFilterFieldCatalog`, **when** imported, **then** it returns `DeletedFieldReferences` and does not save.

Cover every field-bearing construct present in the repository's filter model, such as predicates, sorting, grouping, aggregation, and visible-field configuration.

### Slice 6: Valid import

**Given** a V1 document whose references all resolve to active fields, **when** imported, **then** it creates a canonical saved filter through the existing persistence seam and returns its normal import projection.

### Slice 7: Field-type binding

**Given** an active field with an incompatible operator or value, **when** imported, **then** it returns `InvalidSavedFilterDocument` before persistence.

### Slice 8: Authorization and scope

**Given** an unauthorized actor or incompatible destination scope, **when** import or export is requested, **then** the existing authorization behavior is preserved and no data is disclosed or persisted.

### Slice 9: Idempotent import retry

**Given** an import request ID whose initial create committed, **when** the same request is retried, **then** it returns the original saved filter and creates no duplicate.

Use the representative local database when uniqueness or transaction behavior is claimed.

### Slice 10: Protocol and UI boundary

- Export response has `application/json` and a safe `.json` filename.
- Import endpoint correctly projects malformed JSON, unknown version, and deleted-field typed errors.
- Representative UI test verifies selecting a valid file reaches the import seam and displays the repository-standard result.

### Property Coverage

Where the existing test stack supports it:

```txt
for every valid canonical saved filter whose referenced fields remain active:
  parseSavedFilterPortableDocument(JSON.stringify(toSavedFilterPortableV1(filter)))
  -> bindActiveFields(...)
  -> canonical definition equivalent to the original portable projection
```

## Risks and Open Questions

1. **Portable filter shape:** The exact filter AST, field-bearing nodes, and existing parser must be inspected before defining `PortableSavedFilterDefinitionV1`.
2. **Filter scope:** If filters are scoped to a list, entity type, workspace, or data source, determine whether V1 embeds a portable scope discriminator or import always targets the current scope.
3. **Deleted versus unavailable fields:** The field-catalog adapter should treat every non-active referenced field as rejected. Confirm whether the product needs a user-visible distinction between deleted, inaccessible, and never-existing fields.
4. **Literal values:** Confirm whether saved-filter values can contain sensitive business data. Regardless, they must not be emitted to telemetry or error output.
5. **Idempotency storage:** Reuse existing mutation idempotency if available; otherwise add a minimal transactional receipt with repository-approved schema and retention policy.
6. **Protocol details:** Reuse existing route, server-action, upload size limit, download, error-status, and localization conventions rather than introducing parallel infrastructure.

**Deviations:** none.
