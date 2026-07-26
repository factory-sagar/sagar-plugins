# Architecture Scan

Scope: the entire small billing service. I inspected all source files, `README.md`, required architecture standards, async guidance, and test locations. No tests, ADRs, or context files exist.

### 1. Create an invoice-charging service boundary: **Strong**

- **Standards areas:** Designing Modules; Boundaries and Parsing; Error Handling; Async and Workflows
- **Files/modules:** `src/billing/invoice.js`, `src/http/routes.js`, `src/jobs/retry.js`
- **Current friction:** `finalizeInvoice` is nominally billing logic but accepts a raw HTTP request, parses JSON, calls Stripe, writes SQL, sends email, generates a timestamp, and returns a vendor-shaped charge. Both HTTP and retry jobs must use this HTTP-coupled entrypoint.
- **Evidence:** `handleInvoicePost -> finalizeInvoice(req)` in `src/http/routes.js:5-7`; `retryFailed -> finalizeInvoice(request)` in `src/jobs/retry.js:5-7`; all orchestration is combined in `src/billing/invoice.js:6-14`.
- **Refactor direction:** Make billing own a cohesive parsed invoice-charge command and the orchestration policy. Keep HTTP parsing/projection and job payload handling in their respective adapters; inject narrow payment, invoice-store, email, clock, and job seams.
- **Expected leverage:** Removes raw-request and vendor knowledge from billing callers, centralizes the charge-to-invoice policy, and makes the same use case usable from HTTP and retries.
- **Likely test strategy:** Exercise the billing module through its public command interface with recording payment, storage, email, and clock adapters.
- **Follow-up tech-spec should decide:** Command and result contracts, dependency seams, whether sending the receipt is required for success, and precise expected-failure outcomes.

### 2. Model retry safety and receipt delivery explicitly: **Strong**

- **Standards areas:** Async and Workflows; Error Handling; Designing Modules
- **Files/modules:** `src/jobs/retry.js`, `src/billing/invoice.js`
- **Current friction:** Retrying repeats a charge with no idempotency or persisted progress, and receipt delivery is a floating promise with ignored failure.
- **Evidence:** `retryFailed` invokes `finalizeInvoice(request).catch(() => {})` without awaiting or managed detached-work ownership in `src/jobs/retry.js:4-8`. `finalizeInvoice` charges before persisting and invokes `sendEmail` without awaiting it in `src/billing/invoice.js:9-13`.
- **Refactor direction:** Give the invoice lifecycle an explicit, retry-safe ownership model, including a stable idempotency key or transition guard and an owned receipt-delivery path.
- **Expected leverage:** Prevents duplicate charges after retry and makes delivery failures visible, recoverable, and observable instead of silently lost.
- **Likely test strategy:** Behavior tests through the billing service and a real job seam, proving duplicate delivery does not create another charge and email failures have a defined outcome.
- **Follow-up tech-spec should decide:** Idempotency key source, persisted invoice states, atomic transition semantics, retry owner/lifetime, and receipt failure policy.

### 3. Establish explicit HTTP and persistence boundaries: **Strong**

- **Standards areas:** Boundaries and Parsing; Error Handling; Designing Modules
- **Files/modules:** `src/http/routes.js`, `src/billing/invoice.js`, `src/db.js`
- **Current friction:** Unknown HTTP JSON flows directly into charging and interpolated SQL, while raw database rows flow directly to an HTTP response. No layer owns parsing or projections.
- **Evidence:** `JSON.parse(rawRequest.body)` and use of `payload.card_token`, `payload.customer`, and `payload.email` in `src/billing/invoice.js:7-13`; direct interpolated `INSERT` in `src/billing/invoice.js:10-12`; `handleInvoiceList` maps raw `db.query` rows directly to JSON in `src/http/routes.js:10-15`.
- **Refactor direction:** Parse requests at the HTTP adapter into canonical billing values; put invoice persistence projections and row reconstruction in the database adapter; make HTTP response projection explicit.
- **Expected leverage:** Makes boundary trust explicit, removes raw rows and payloads from core logic, and creates one safe location for field validation and SQL parameterization.
- **Likely test strategy:** Parser tests for accepted/rejected commands, adapter tests for parameterized persistence projections, and handler tests for public response shapes.
- **Follow-up tech-spec should decide:** Canonical invoice values, required validation rules, storage schema assumptions, parse-failure representation, and public response contract.

### 4. Put invoice presentation in one owner: **Worth exploring**

- **Standards areas:** Designing Modules; Boundaries and Parsing
- **Files/modules:** `src/billing/invoice.js`, `src/http/routes.js`
- **Current friction:** Invoice amount formatting is exported from billing but reimplemented in the HTTP list handler, so two locations own presentation behavior.
- **Evidence:** `formatCents` exists in `src/billing/invoice.js:17-19`, while `src/http/routes.js:15` independently constructs the same dollar formatting and does not use its import.
- **Refactor direction:** After the service and projections are separated, assign currency display formatting to the HTTP projection or a dedicated neutral money-value module, rather than the current mixed billing module.
- **Expected leverage:** Removes duplicate formatting policy and avoids exposing unrelated presentation helpers from billing orchestration.
- **Likely test strategy:** Test the selected projection or value module with representative cent values through its public interface.
- **Follow-up tech-spec should decide:** Whether currency is a domain value, the display locale/currency contract, and whether API consumers receive formatted totals or raw cents.

**Top recommendation:** Create an invoice-charging service boundary. It has the broadest leverage because it removes the raw HTTP coupling that currently forces both routes and retries through the same unsafe, multi-responsibility function.
