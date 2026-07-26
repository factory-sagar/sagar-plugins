Summary:
The importer violates its caller-facing typed-outcome contract and trusts unvalidated JSON. These issues can turn expected import failures into rejected promises or runtime exceptions.

Assessment: needs changes

What This Change Does:
- Parses a saved-filter JSON string.
- Rejects unsupported versions and references to unavailable fields.
- Returns the parsed filter when validation succeeds.

Coverage:
- Read in full: `src/importSavedFilter.ts` (reconstructed from the complete new-file diff)
- Skimmed (with reason): none
- Not looked at (and why): callers and existing tests were not included
- Tests run: none — static review only
- Selected-lens evidence: Caller-facing typed outcomes are violated by thrown errors at `src/importSavedFilter.ts:10-16`.
- Changed-file accounting: `src/importSavedFilter.ts` inspected in full

Findings:
- [P1·high] Expected import outcomes reject instead of returning typed values — `src/importSavedFilter.ts:10-16`
  Scope: in-scope fix
  Why: Unsupported versions and missing field references are explicitly normal outcomes for the caller, but both branches throw. Because the function is `async`, these become rejected promises rather than typed return variants.
  Impact: The surrounding workflow cannot exhaustively handle these outcomes through its expected result channel.
  Follow-up: Return distinct typed variants for unsupported versions and missing field IDs, and expose them in the function’s return type.

- [P1·high] Serialized input is trusted without runtime parsing — `src/importSavedFilter.ts:8`
  Scope: in-scope fix
  Why: `JSON.parse(rawJson) as SavedFilter` provides no runtime proof. Missing `fieldIds` causes an exception at line 14, a missing `name` is returned as a supposedly valid filter, and malformed JSON throws directly.
  Impact: Invalid imported data can escape as a `SavedFilter` or bypass typed failure handling through exceptions.
  Follow-up: Parse into `unknown`, validate every required property, and translate parse failures into the established typed outcome channel.

- [P2·high] New failure contracts lack regression coverage — `src/importSavedFilter.ts:7-19`
  Scope: in-scope fix
  Why: The supplied diff introduces a new public import boundary without tests covering its success and expected-failure paths.
  Impact: Return-channel regressions such as the current thrown errors can reach merge undetected.
  Follow-up: Add interface-level tests for valid input, unsupported versions, missing field references, malformed JSON, and missing or invalid properties.

Validation Notes:
- Commands run: none; review used the supplied diff and read-only file tools
- Standards loaded: `coding-standards/SKILL.md`, `BOUNDARIES_AND_PARSING.md`, `ERROR_HANDLING.md`, `ASYNC_AND_WORKFLOWS.md`, `TESTING_AND_VERIFICATION.md`, `TYPE_CONTRACTS.md`, `VOCABULARY.md`
- Hand-off to `security`: none
- Hand-off to `deep-understanding`: none
- Wrong-droid call by parent: no
- Caveats: No repository, callers, or tests were supplied; the caller contract in the request was treated as authoritative.
- Pre-existing issues spotted (out of scope): none
