# Golden Task 03: Architecture Scan

Version: 2

## Target

`architecture-scan`.

## Setup

```bash
mkdir -p src/billing src/http src/jobs
cat > src/billing/invoice.js <<'JS'
const db = require('../db');
const stripe = require('../vendor/stripe');
const { sendEmail } = require('../mail');

// Charges the card, writes the row, emails the customer, and formats the PDF filename.
async function finalizeInvoice(rawRequest) {
  const payload = JSON.parse(rawRequest.body);
  const amount = payload.amount_cents;
  const charge = await stripe.charge(payload.card_token, amount);
  await db.query(
    `INSERT INTO invoices (customer, cents, charge_id) VALUES ('${payload.customer}', ${amount}, '${charge.id}')`,
  );
  sendEmail(payload.email, `invoice-${payload.customer}-${Date.now()}.pdf`);
  return { ok: true, charge };
}

function formatCents(cents) {
  return `$${(cents / 100).toFixed(2)}`;
}

module.exports = { finalizeInvoice, formatCents };
JS
cat > src/http/routes.js <<'JS'
const { finalizeInvoice, formatCents } = require('../billing/invoice');
const db = require('../db');

// Route handlers reach into the database directly and re-implement formatting.
async function handleInvoicePost(req, res) {
  const result = await finalizeInvoice(req);
  res.json(result);
}

async function handleInvoiceList(req, res) {
  const rows = await db.query('SELECT * FROM invoices');
  res.json(rows.map((r) => ({ ...r, total: `$${(r.cents / 100).toFixed(2)}` })));
}

module.exports = { handleInvoicePost, handleInvoiceList, formatCents };
JS
cat > src/jobs/retry.js <<'JS'
const { finalizeInvoice } = require('../billing/invoice');

// Fire-and-forget retries with no ownership of the resulting promise.
function retryFailed(requests) {
  for (const request of requests) {
    finalizeInvoice(request).catch(() => {});
  }
  return 'scheduled';
}

module.exports = { retryFailed };
JS
cat > src/db.js <<'JS'
module.exports = { query: async () => [] };
JS
mkdir -p src/vendor
cat > src/vendor/stripe.js <<'JS'
module.exports = { charge: async () => ({ id: 'ch_test' }) };
JS
cat > src/mail.js <<'JS'
module.exports = { sendEmail: () => undefined };
JS
cat > package.json <<'JSON'
{ "name": "billing-service", "version": "1.0.0", "scripts": { "test": "echo no tests" } }
JSON
cat > README.md <<'MD'
# billing-service

Charges invoices. No test suite yet.
MD
```

## Prompt

```text
Look through this repo and tell me where the architecture most needs simplification. Do not change code yet.
```

## Expected behavior

The agent should perform a planning-only scan, load relevant standards topics, inspect evidence, and return ranked refactor candidates. It should not implement or estimate speculative effort.

## Must pass

- States the scan scope and confirms it is planning-only.
- Loads or references relevant `coding-standards` topics for module boundaries, type contracts, testing, and async or parsing where applicable.
- Uses file-path evidence for each candidate.
- Ranks candidates by confidence or value.
- Includes why each candidate matters, what would improve, and what a follow-up `tech-spec` should decide.
- Recommends at most 5 candidates.

## Must not do

- Edit files or propose patches.
- Give vague advice without file evidence.
- Estimate calendar effort as if it were a project plan.
- Treat all findings as equally important.
- Turn the scan into a general code review of every style nit.

## Score

- `pass`: ranked evidence-backed candidates are returned and no implementation occurs.
- `partial`: candidates are useful but one lacks concrete file evidence.
- `fail`: the agent edits files, produces broad advice only, or skips standards-backed reasoning.
