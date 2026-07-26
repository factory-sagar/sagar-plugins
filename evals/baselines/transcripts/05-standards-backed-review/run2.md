Summary: The importer violates its caller-facing contract by rejecting for expected outcomes and trusts unvalidated JSON. The new behavior also lacks tests.

Assessment: needs changes

What This Change Does:
- Parses a saved-filter JSON string.
- Rejects unsupported versions and references to unavailable fields.
- Returns the imported filter when validation succeeds.

Coverage:
- Read in full: `src/importSavedFilter.ts` (complete supplied new file)
- Skimmed (with reason): none
- Not looked at (and why): callers and repository tests were not supplied
- Tests run: none — static review only
- Selected-lens evidence: Caller-facing typed outcomes fail at `src/importSavedFilter.ts:10-17`; boundary parsing is unsafe at `src/importSavedFilter.ts:7-14`.
- Changed-file accounting: `src/importSavedFilter.ts` inspected in full

Findings:
- [P1·high] Expected outcomes become rejected promises — `src/importSavedFilter.ts:10-17`
  Scope: in-scope fix
  Why: Unsupported versions and missing referenced fields are explicitly caller-handled expected outcomes, but this async function throws raw `Error` objects. Its inferred return type only exposes `Promise<SavedFilter>`.
  Impact: The caller cannot distinguish these outcomes through its typed workflow and instead receives unexpected promise rejections.
  Follow-up: Return both cases through the repository’s established typed result channel, using distinct variants the caller can exhaustively handle.

- [P1·high] Decoded JSON bypasses runtime parsing — `src/importSavedFilter.ts:7`
  Scope: in-scope fix
  Why: `JSON.parse(rawJson) as SavedFilter` asserts untrusted data satisfies the domain type. Inputs such as `{}` or `{"version":"v1"}` reach `parsed.fieldIds.filter` and throw `TypeError`; malformed JSON also escapes through an exception.
  Impact: Invalid or incomplete imports bypass the expected failure channel and may crash the workflow.
  Follow-up: Parse the decoded value from `unknown`, validate every required property and element type, and return parse failures through the typed outcome contract.

- [P2·high] New boundary and failure behavior has no tests — `src/importSavedFilter.ts:7-19`
  Scope: in-scope fix
  Why: The supplied diff adds no tests for successful import, unsupported versions, missing referenced fields, malformed JSON, or incomplete shapes.
  Impact: The two contract violations above can merge without regression evidence.
  Follow-up: Add caller-facing behavior tests asserting typed outcomes for every success and failure path.

Validation Notes:
- Commands run: none; the supplied new-file diff was reviewed directly
- Standards loaded: `coding-standards/SKILL.md`, `VOCABULARY.md`, `BOUNDARIES_AND_PARSING.md`, `ERROR_HANDLING.md`, `ASYNC_AND_WORKFLOWS.md`, `TESTING_AND_VERIFICATION.md`, `TYPE_CONTRACTS.md`
- Hand-off to `security`: none
- Hand-off to `deep-understanding`: none
- Wrong-droid call by parent: no
- Caveats: Repository callers and existing test conventions were unavailable; the explicit caller contract was sufficient to establish the findings.
- Pre-existing issues spotted (out of scope): none
