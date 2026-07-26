Summary: The importer violates the stated caller contract by rejecting for expected failures and trusting unvalidated JSON.

Assessment: needs changes

What This Change Does:
- Parses a serialized saved filter.
- Rejects unsupported versions and unresolved field IDs.
- Returns the imported filter on success.

Coverage:
- Read in full: `src/importSavedFilter.ts`
- Skimmed (with reason): none
- Not looked at (and why): none within the supplied diff
- Tests run: none — static review only
- Selected-lens evidence: Expected-failure paths at `src/importSavedFilter.ts:10-17` throw instead of returning typed outcomes.
- Selected-lens evidence: Boundary input is cast without validation at `src/importSavedFilter.ts:8`; dereferences occur at lines 10 and 14.
- Selected-lens evidence: Success, unsupported-version, missing-field, and malformed-input paths were inspected.
- Changed-file accounting: `src/importSavedFilter.ts` inspected in full.
- Untracked-file accounting: n/a, only a textual diff was supplied.

Findings:
- [P1·high] Expected outcomes are exposed as rejected promises — `src/importSavedFilter.ts:10-17`
  Scope: in-scope fix
  Why: Unsupported versions and missing field IDs are ordinary caller-handled outcomes, but both branches throw generic `Error` values. Because the function is `async`, its inferred contract is only `Promise<SavedFilter>`.
  Impact: Callers cannot exhaustively handle these outcomes through the return type and must classify exceptions or error-message strings.
  Follow-up: Return a precise tagged result union containing the unsupported-version and missing-field variants.

- [P1·high] Serialized input is trusted through an unchecked cast — `src/importSavedFilter.ts:8`
  Scope: in-scope fix
  Why: `JSON.parse(rawJson) as SavedFilter` provides no runtime proof. For example, `{"version":"v1"}` reaches `parsed.fieldIds.filter` and throws a `TypeError`, bypassing semantic outcome handling.
  Impact: Malformed persisted input can escape through undocumented exceptions rather than a typed parse failure.
  Follow-up: Parse the decoded value from `unknown`, validate every required field, and include parse failure in the typed result.

Validation Notes:
- Commands run: none
- Standards loaded: `coding-standards/SKILL.md`, `VOCABULARY.md`, `BOUNDARIES_AND_PARSING.md`, `ERROR_HANDLING.md`, `ASYNC_AND_WORKFLOWS.md`, `TESTING_AND_VERIFICATION.md`, `TYPE_CONTRACTS.md`
- Hand-off to `security`: none
- Hand-off to `deep-understanding`: none
- Wrong-droid call by parent: no
- Caveats: Only the supplied textual diff was available, so callers and existing tests could not be traced.
- Pre-existing issues spotted (out of scope): none
