# Architecture Scan

**Scope:** all six `src` modules. No ADRs or tests exist. Per the scan contract, no code or checks were run.

```txt
HTTP / retry request
  -> finalizeInvoice(raw request)
     -> Stripe charge -> DB insert -> email

HTTP list route
  -> DB rows -> HTTP response
```

### Extract invoice finalization into a service with explicit adapters: Strong

- **Standards areas:** Module, boundary, failure, async, test seam
- **Files/modules:** `src/billing/invoice.js:1-14`, `src/http/routes.js:5-7`, `src/jobs/retry.js:1-8`
- **Current friction:** `finalizeInvoice` accepts an HTTP-shaped request, parses JSON, invokes Stripe, constructs SQL, sends mail, and generates a timestamped filename. Both the HTTP route and retry job must understand and supply that raw request shape.
- **Evidence:** The function imports hidden global dependencies at `invoice.js:1-3`, parses `rawRequest.body` at line 7, sequences all effects at lines 9-13, and is invoked by both HTTP and job entrypoints.
- **Refactor direction:** Make invoice finalization a cohesive service that accepts a parsed invoice command and narrow payment, persistence, mail, and clock/filename dependencies. Keep HTTP and retry parsing, response rendering, and job ownership in their respective adapters.
- **Expected leverage:** One owner for charging, persistence, notification policy, and dependency-failure translation. Entrypoints no longer need to know the workflow’s internal sequencing or infrastructure.
- **Likely test strategy:** Exercise the service through injected recording/fake payment, invoice-store, mail, and clock seams, asserting result values and recorded effects.
- **Follow-up tech-spec should decide:** Parsed command shape, payment and persistence outcomes, notification failure policy, invoice lifecycle and retry/idempotency semantics, and cancellation propagation.
- **Context/ADR note:** No ADRs found. Record a decision only if this introduces a new adapter-provisioning or persistence model.

### Make invoice creation retry-safe and own retry work: Strong

- **Standards areas:** Async workflow, state, failure, test seam
- **Files/modules:** `src/jobs/retry.js:3-8`, `src/billing/invoice.js:9-13`
- **Current friction:** The retry job starts unowned promises, discards every failure, and reuses the same charge-and-insert workflow without a visible idempotency key or lifecycle guard.
- **Evidence:** `retryFailed` calls `finalizeInvoice(request).catch(() => {})` at `retry.js:6`; finalization charges before inserting at `invoice.js:9-12`, so a retry after a charge-side success but before persistence can duplicate a charge.
- **Refactor direction:** Replace fire-and-forget dispatch with an explicitly owned retry mechanism that records outcomes. Have the invoice service accept a stable logical identity or idempotency key and use a persistence-backed transition/replay guard before external effects.
- **Expected leverage:** Eliminates silent job failures and duplicate-charge ambiguity while concentrating retry policy with the workflow it affects.
- **Likely test strategy:** Call the job/service through real seams with recording adapters, covering a retried command, a charge success followed by persistence failure, and a mail failure.
- **Follow-up tech-spec should decide:** Retry owner and lifetime, result reporting, idempotency key source, allowed invoice states, durable state/transition guard, and treatment of partial effects.
- **Context/ADR note:** Durable retry/idempotency design is a material architecture decision.

### Separate HTTP and persistence projections from invoice data: Worth exploring

- **Standards areas:** Boundary parsing, module, state, test seam
- **Files/modules:** `src/http/routes.js:9-12`, `src/billing/invoice.js:17-18`
- **Current friction:** The list route forwards database rows directly to HTTP clients, spreads their complete shape, and embeds currency formatting. Formatting is also defined in `invoice.js` but not reused.
- **Evidence:** `handleInvoiceList` reads `SELECT *` at `routes.js:11` and returns `{ ...r, total: ... }` at line 12. `formatCents` already exists at `invoice.js:17-18`, while the route reimplements equivalent formatting inline.
- **Refactor direction:** Define an invoice read model/domain representation reconstructed from storage rows, then give the HTTP adapter a named projection that selects the public fields and formats amounts consistently.
- **Expected leverage:** Stops storage-schema changes from leaking into the API, localizes currency presentation, and gives consumers a stable response contract.
- **Likely test strategy:** Test storage-row reconstruction and HTTP projection through their interfaces, including rejected contradictory rows and public-field selection.
- **Follow-up tech-spec should decide:** Public invoice fields, currency/locale policy, stored-state invariants, missing-row behavior, and whether list queries should return a purpose-built read projection.
- **Context/ADR note:** None unless the read model becomes a distinct persistence architecture.

## Top Recommendation

Start with **extracting invoice finalization into an explicit service with adapters**. It is the highest-leverage simplification because it removes raw HTTP, database, payment, email, and time concerns from the shared workflow, while creating the seam needed to address the retry and idempotency defect safely.
