Summary: The importer violates its caller-facing contract by rejecting expected outcomes and trusting unvalidated JSON.

Assessment: needs changes

What This Change Does:
- Decodes a saved filter from JSON.
- Rejects unsupported versions and missing field references.
- Returns the decoded filter when checks pass.

Coverage:
- Read in full: `src/importSavedFilter.ts`
- Skimmed (with reason): none
- Not looked at (and why): none within the supplied diff; callers and repository tests were unavailable
- Tests run: none — static review only
- Selected-lens evidence:
  - Boundary parsing and type contracts: `src/importSavedFilter.ts:7-8`, Finding 2
  - Expected failures and async behavior: `src/importSavedFilter.ts:10-16`, Finding 1
  - Success path: `src/importSavedFilter.ts:19`, clean assuming correctly shaped input
  - Test coverage: no tests accompanied the new module, Finding 3
- Changed-file accounting: `src/importSavedFilter.ts`, complete new file inspected

Findings:
- [P1·high] Expected outcomes reject the promise instead of using the workflow’s typed channel: `src/importSavedFilter.ts:10-16`
  Scope: in-scope fix
  Why: Unsupported versions and missing fields are declared normal caller-handled outcomes, but both branches throw. Because the function is `async`, these become rejected promises and are absent from its inferred success-only return type.
  Impact: The surrounding workflow cannot exhaustively distinguish these expected outcomes through its typed result handling.
  Follow-up: Return the repository’s precise tagged result or error union for unsupported versions and missing fields.

- [P1·high] Serialized input is trusted without runtime parsing: `src/importSavedFilter.ts:7-14`
  Scope: in-scope fix
  Why: `JSON.parse(rawJson) as SavedFilter` provides no runtime proof. Malformed JSON throws, while values such as `null`, missing `fieldIds`, or non-array `fieldIds` cause unclassified exceptions when properties are accessed.
  Impact: Ordinary invalid import data can escape as `SyntaxError` or `TypeError` instead of a stable typed import outcome.
  Follow-up: Decode to `unknown`, parse the complete shape at this boundary, and classify syntax and schema failures into the typed outcome channel.

- [P2·medium] New boundary and failure behavior lacks test evidence: `src/importSavedFilter.ts:7-19`
  Scope: in-scope fix
  Why: The supplied change contains no caller-facing tests for its parsing and expected-failure branches.
  Impact: Rejected promises could replace typed outcomes without regression detection.
  Follow-up: Add behavior tests covering valid input, malformed or incomplete shapes, unsupported versions, and missing referenced fields, asserting typed outcomes through the exported function.

Validation Notes:
- Commands run: none; review used the supplied inline diff and read-only file inspection
- Standards loaded: `coding-standards/SKILL.md`, `BOUNDARIES_AND_PARSING.md`, `ERROR_HANDLING.md`, `ASYNC_AND_WORKFLOWS.md`, `TYPE_CONTRACTS.md`, `TESTING_AND_VERIFICATION.md`, `VOCABULARY.md`
- Hand-off to `security`: none
- Hand-off to `deep-understanding`: none
- Wrong-droid call by parent: no
- Caveats: The evaluation workspace contained no source tree, callers, or existing tests, so surrounding usage could not be independently traced.
- Pre-existing issues spotted (out of scope): none
