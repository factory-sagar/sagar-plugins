Summary: The importer violates its caller-facing contract by rejecting expected outcomes and trusting unvalidated JSON. These issues can crash the workflow or return malformed data.

Assessment: needs changes

What This Change Does:
- Parses a saved-filter JSON string.
- Rejects unsupported versions and references to unavailable fields.
- Returns the imported filter when checks pass.

Coverage:
- Read in full: `src/importSavedFilter.ts` from the supplied diff
- Skimmed (with reason): none
- Not looked at (and why): none within the supplied scope
- Tests run: none — static review only
- Selected-lens evidence:
  - Error contract: expected outcomes throw at `src/importSavedFilter.ts:9-15`.
  - Boundary parsing and type safety: decoded JSON is cast without validation at `src/importSavedFilter.ts:7`.
  - Async/API contract: inferred `Promise<SavedFilter>` omits expected failures at `src/importSavedFilter.ts:6-18`.
  - Test coverage: no tests accompany the new importer or its failure paths.
- Changed-file accounting: `src/importSavedFilter.ts` inspected completely as a new file.

Findings:
- [P1·high] Expected outcomes escape as rejected promises — `src/importSavedFilter.ts:9-15`
  Scope: in-scope fix
  Why: Unsupported versions and unavailable field references are explicitly caller-handled outcomes, but both paths throw. Because the function is `async`, callers receive rejected promises rather than typed variants.
  Impact: The workflow cannot exhaustively handle these expected outcomes through its declared return contract, and an omitted catch becomes an exception path.
  Follow-up: Return the workflow’s established typed variants for unsupported versions and missing field IDs, reserving rejection for defects.

- [P1·high] Untrusted JSON is asserted as a valid saved filter — `src/importSavedFilter.ts:7`
  Scope: in-scope fix
  Why: `JSON.parse(rawJson) as SavedFilter` supplies no runtime proof. For example, `{"version":"v1"}` crashes when `.filter` is called, while a numeric `name` or non-string field ID can pass through as `SavedFilter`.
  Impact: Malformed saved data can either produce unclassified exceptions or leak invalid values into downstream code.
  Follow-up: Parse the decoded value from `unknown`, validate every required field and collection element, and classify parse failures through the typed outcome channel.

- [P2·high] New boundary and failure behavior lacks tests — `src/importSavedFilter.ts:6-18`
  Scope: in-scope fix
  Why: The diff contains no behavior tests for valid input, malformed JSON, invalid shapes, unsupported versions, or missing referenced fields.
  Impact: The caller-facing typed-outcome contract and parser invariants can regress undetected.
  Follow-up: Add interface-level tests asserting successful imports and each typed failure variant without relying on thrown exceptions.

Validation Notes:
- Commands run: none; the complete diff was supplied inline.
- Standards loaded: `coding-standards/SKILL.md`, `BOUNDARIES_AND_PARSING.md`, `ERROR_HANDLING.md`, `ASYNC_AND_WORKFLOWS.md`, `TYPE_CONTRACTS.md`, `TESTING_AND_VERIFICATION.md`
- Hand-off to `security`: none
- Hand-off to `deep-understanding`: none
- Wrong-droid call by parent: no
- Caveats: Repository callers and existing result conventions were unavailable, so tracing used the explicit caller-facing contract supplied with the diff.
- Pre-existing issues spotted (out of scope): none
