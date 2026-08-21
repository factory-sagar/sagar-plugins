# Golden Task 05: Standards-backed Review

Version: 2

## Target

`change-review`.

## Prompt

```text
Review this diff. Static review only. This import sits behind a caller-facing workflow that
handles unsupported versions and missing fields as expected typed outcomes rather than
exceptions.

diff --git a/src/importSavedFilter.ts b/src/importSavedFilter.ts
new file mode 100644
--- /dev/null
+++ b/src/importSavedFilter.ts
@@
+type SavedFilter = {
+  version: "v1";
+  name: string;
+  fieldIds: string[];
+};
+
+export async function importSavedFilter(rawJson: string, existingFieldIds: string[]) {
+  const parsed = JSON.parse(rawJson) as SavedFilter;
+
+  if (parsed.version !== "v1") {
+    throw new Error("Unsupported filter version");
+  }
+
+  const missingFieldIds = parsed.fieldIds.filter((fieldId) => !existingFieldIds.includes(fieldId));
+  if (missingFieldIds.length > 0) {
+    throw new Error(`Missing fields: ${missingFieldIds.join(",")}`);
+  }
+
+  return parsed;
+}
```

## Intent

The run exists to give the caller a high-signal, standards-backed static review of the saved-filter
import's boundary parsing and expected-failure behavior. Success means identifying the unchecked
cast and generic expected errors with concrete impact and follow-up direction; finding the cast
without standards or impact remains partial achievement, while missing it or reporting only style
feedback misses the point.

## Fulfillment

- States that standards topics were loaded or applied, especially boundaries/parsing, error handling, and type contracts.
- Flags the unchecked `JSON.parse(rawJson) as SavedFilter` as a material boundary parsing issue.
- Explains that validation of `version` after a cast does not prove `name` or `fieldIds` are well-formed.
- Flags expected import failures being surfaced as generic thrown errors despite the stated
  caller-handled typed-outcome contract.
- Provides a concrete impact and follow-up direction.
- Uses confidence labels in the required `[P<n>·<conf>]` form.
- Keeps findings capped and high signal.

## Boundaries

- Focus on style nits such as variable names or line length.
- Suggest implementation patches inline.
- Run tests or package commands.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
