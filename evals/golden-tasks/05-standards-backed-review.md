# Golden Task 05: Standards-backed Review

## Target

`change-review`.

## Prompt

```text
Review this diff. Static review only.

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

## Expected behavior

The reviewer should identify the boundary parsing and expected-failure issues. It should ground the finding in standards, not style preferences.

## Must pass

- States that standards topics were loaded or applied, especially boundaries/parsing, error handling, and type contracts.
- Flags the unchecked `JSON.parse(rawJson) as SavedFilter` as a material boundary parsing issue.
- Explains that validation of `version` after a cast does not prove `name` or `fieldIds` are well-formed.
- Flags expected import failures being surfaced as generic thrown errors if the surrounding contract expects caller-handled results.
- Provides a concrete impact and follow-up direction.
- Uses confidence labels in the required `[P<n>·<conf>]` form.
- Keeps findings capped and high signal.

## Must not do

- Focus on style nits such as variable names or line length.
- Suggest implementation patches inline.
- Run tests or package commands.
- Ignore the seeded unchecked-cast issue.

## Score

- `pass`: the seeded boundary/parsing bug is found with standards-backed proof.
- `partial`: the unchecked cast is found but not tied to standards or impact.
- `fail`: the review misses the unchecked cast or reports only style feedback.
