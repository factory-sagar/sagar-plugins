Summary: The importer violates its caller-facing contract by throwing expected failures and trusting decoded JSON without runtime parsing.

Assessment: needs changes

What This Change Does:
- Decodes and imports a saved `v1` filter.
- Rejects unsupported versions and references to missing fields.

Coverage:
- Read in full: `src/importSavedFilter.ts` from the supplied diff
- Skimmed: none
- Not looked at: callers and tests, unavailable in the provided scope
- Tests run: none — static review only
- Selected-lens evidence: Expected typed outcomes are thrown at `src/importSavedFilter.ts:10-17`; boundary input is cast without parsing at `src/importSavedFilter.ts:8`
- Changed-file accounting: `src/importSavedFilter.ts` inspected in full

Findings:
- [P1·high] Expected outcomes escape as rejected promises — `src/importSavedFilter.ts:10-17`
  Scope: in-scope fix
  Why: Unsupported versions and missing fields are normal workflow outcomes, but both paths throw. The inferred return type exposes only `Promise<SavedFilter>`, so callers cannot handle these cases through the promised typed channel.
  Impact: The caller-facing workflow may bypass its expected-outcome handling and enter exception handling instead.
  Follow-up: Return a precise typed result containing distinct unsupported-version and missing-fields variants. Reserve throwing for defects.

- [P1·high] Decoded JSON is trusted without runtime parsing — `src/importSavedFilter.ts:8`
  Scope: in-scope fix
  Why: `JSON.parse(rawJson) as SavedFilter` provides no runtime proof. Missing or malformed `fieldIds` can cause a `TypeError`, missing `version` is misclassified as unsupported, and an invalid `name` can be returned successfully.
  Impact: Malformed saved data can crash the workflow or produce an invalid domain value.
  Follow-up: Parse the decoded value from `unknown` into the complete saved-filter shape, returning syntax and shape failures through a typed outcome before applying semantic checks.

- [P2·high] New boundary and failure behavior has no tests — `src/importSavedFilter.ts:7`
  Scope: in-scope fix
  Why: The diff adds an importer but no caller-facing behavior tests.
  Impact: Typed failure handling and malformed-input behavior can regress undetected.
  Follow-up: Add interface-level tests for valid input, unsupported versions, missing fields, invalid JSON, and malformed shapes.

Validation Notes:
- Commands run: none; the review target was an inline diff
- Standards loaded: `coding-standards/SKILL.md`, `VOCABULARY.md`, `BOUNDARIES_AND_PARSING.md`, `ERROR_HANDLING.md`, `ASYNC_AND_WORKFLOWS.md`, `TYPE_CONTRACTS.md`, `TESTING_AND_VERIFICATION.md`
- Hand-off to `security`: none
- Hand-off to `deep-understanding`: none
- Wrong-droid call by parent: no
- Caveats: Repository callers and existing test conventions were not provided
- Pre-existing issues spotted (out of scope): none
