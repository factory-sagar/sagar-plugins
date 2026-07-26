# Architecture Simplification Scan

**Scope:** the complete small billing service. I inspected the repository, its README, and the required architecture and coding-standard references. No code was changed or commands run.

### Make invoice finalization a cohesive service module: **Strong**

- **Standards areas:** Designing Modules; Boundaries and Parsing; Error Handling; Async and Workflows
- **Files/modules:** `src/billing/invoice.js`, `src/http/routes.js`, `src/jobs/retry.js`
- **Current friction:** `finalizeInvoice` accepts a raw HTTP-shaped request and directly coordinates payment, SQL construction, email delivery, timestamp-based filename construction, and its response shape. Both HTTP and job callers must supply the same raw-request representation.
- **Evidence:** `src/billing/invoice.js:6-14` parses `rawRequest.body`, calls Stripe, persists a row, and sends email. `src/http/routes.js:5-7` and `src/jobs/retry.js:4-6` call it from distinct entrypoints.
- **Refactor direction:** Establish an invoice-finalization service module that receives a parsed invoice command and explicit narrow dependencies. Keep HTTP parsing/projection in routes, and job payload parsing in the retry entrypoint.
- **Expected leverage:** One owner for the use-case policy, a small caller-facing interface shared by HTTP and jobs, and a real seam for payment, storage, email, and time.
- **Likely test strategy:** Exercise the service with recording payment, invoice-store, email, and clock adapters; separately test HTTP and job parsing/projections.
- **Follow-up tech-spec should decide:** Canonical command/result types, dependency contracts, expected failure union, whether email is part of the synchronous command, and caller-owned cancellation.
- **Context/ADR note:** Define “invoice finalization” as the use case that owns the charge, persistence, and receipt-delivery policy.

```txt
Current:  HTTP request / retry payload -> finalizeInvoice -> Stripe + SQL + email
Proposed: HTTP/job adapter -> parsed InvoiceFinalization -> service -> narrow adapters
```

### Make charging retry-safe and give background work an owner: **Strong**

- **Standards areas:** Async and Workflows; Error Handling; Observability
- **Files/modules:** `src/jobs/retry.js`, `src/billing/invoice.js`
- **Current friction:** Retrying a mutating command can charge a card, insert another invoice row, and send another email. The job loop also discards rejections, making failures invisible.
- **Evidence:** `src/jobs/retry.js:4-7` invokes `finalizeInvoice` without awaiting or collecting its promise, then suppresses every failure with `.catch(() => {})`. `src/billing/invoice.js:9-13` performs three external side effects without an idempotency key, persisted lifecycle state, or failure classification.
- **Refactor direction:** Model invoice finalization as a retry-safe command with a stable idempotency identity and owned job execution. Persist command progress or use an equivalent durable mechanism so retries cannot duplicate a charge, invoice, or receipt.
- **Expected leverage:** Correct behavior after timeout, redelivery, or process failure, plus diagnosable job outcomes instead of silent loss.
- **Likely test strategy:** Use recording payment and email adapters with a real or representative persistence seam to prove repeated delivery yields one charge and one receipt, while dependency failures remain observable.
- **Follow-up tech-spec should decide:** Idempotency-key source, durable state model, transaction/outbox boundary, retry ownership, concurrency limit, cancellation propagation, and safe job telemetry.
- **Context/ADR note:** Record the durable definition of “invoice finalization is idempotent” once chosen.

### Move persistence and HTTP projections to their boundaries: **Worth exploring**

- **Standards areas:** Boundaries and Parsing; Designing Modules
- **Files/modules:** `src/billing/invoice.js`, `src/http/routes.js`, `src/db.js`
- **Current friction:** SQL is assembled in invoice business logic, route code reads raw rows directly, and money formatting is duplicated rather than owned as a named projection.
- **Evidence:** `src/billing/invoice.js:10-11` builds an `INSERT` from invoice values. `src/http/routes.js:10-12` issues `SELECT *` and spreads database rows directly into HTTP output. `formatCents` is exported from `src/billing/invoice.js:17-21`, but the list handler reimplements it at `src/http/routes.js:12`.
- **Refactor direction:** Introduce a cohesive invoice persistence adapter that owns persistence projection and row reconstruction, and keep HTTP response projection in the route adapter. Have the service consume invoice-oriented storage behavior rather than `db.query`.
- **Expected leverage:** Prevents persistence records from leaking to HTTP, centralizes monetary presentation policy, and makes storage behavior independently testable through a narrow seam.
- **Likely test strategy:** Verify persistence round trips and rejection of contradictory stored rows through the invoice-store interface; verify the route’s protocol projection from service results.
- **Follow-up tech-spec should decide:** Invoice domain representation, row/protocol projections, query capability boundaries, and whether formatted totals are an API or UI concern.

## Top recommendation

**Make invoice finalization a cohesive service module.** It has the broadest leverage because it removes raw HTTP coupling from both callers and creates the natural seam required to address retry safety, errors, persistence, external charging, email delivery, and testing.

Select a candidate for the follow-up tech-spec brief.

**Deviations:** none.
