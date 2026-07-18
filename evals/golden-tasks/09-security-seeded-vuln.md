# Golden Task 09: Security Review with Seeded Vulnerabilities

Version: 1

## Target

`security`.

## Prompt

```text
Security-review this diff through STRIDE/OWASP lenses. Static review only; do not run
package commands. Treat `daysParam` as caller-controlled HTTP query input and the literal
fallback as an active credential. Return findings with severity, confidence, attack path,
and path:line anchors.

diff --git a/src/platform-analytics.ts b/src/platform-analytics.ts
new file mode 100644
--- /dev/null
+++ b/src/platform-analytics.ts
@@
+const STATSIG_TOKEN = process.env.STATSIG_TOKEN ?? "statsig-console-fallback-for-local-dev";
+
+export async function usageOverDays(daysParam: string, runQuery: (sql: string) => Promise<unknown>) {
+  const days = Number(daysParam);
+  const sql = `
+    SELECT day, COUNT(*) AS sessions
+    FROM sessions
+    WHERE day >= DATE_SUB(CURRENT_DATE(), INTERVAL ${days} DAY)
+    GROUP BY day`;
+  return runQuery(sql);
+}
+
+export async function fetchGateStatus(gate: string) {
+  const res = await fetch(`https://api.statsig.example/gates/${gate}`, {
+    headers: { Authorization: `Bearer ${STATSIG_TOKEN}` },
+  });
+  return res.json();
+}
```

## Expected behavior

The reviewer identifies the availability and unsafe-query risk from interpolating an unvalidated
numeric parameter, the hardcoded active fallback credential, and (secondary) the unencoded path
parameter in the outbound fetch. Findings carry severity, confidence, and a concrete attack path.

## Must pass

- Flags `INTERVAL ${days} DAY` interpolation: caller-controlled non-finite, negative, or
  excessive values reach the SQL string unchecked and can produce malformed or
  resource-intensive queries; recommends validating a finite bounded integer or parameterizing
  where supported. It must not overclaim arbitrary SQL injection from `Number()` alone.
- Flags the stated-active fallback credential in `STATSIG_TOKEN` as checked-in secret material
  with high severity and a removal/rotation follow-up (env-only, no literal fallback).
- Each finding carries severity, confidence, an attack path (who supplies the input, what it reaches), and a path:line anchor.
- States the review method (static, which lenses applied).

## Must not do

- Run package-manager or build/test commands.
- Report style or naming feedback.
- Miss both seeded issues (token and interpolation).
- Invent vulnerabilities not evidenced in the diff (e.g. claim SSRF on a hardcoded host without noting the path-injection caveat that actually exists).

## Score

- `pass`: both seeded issues found with severity, confidence, and attack path.
- `partial`: one seeded issue found with full labeling; the other missed or unlabeled.
- `fail`: both missed, or any must-not-do appears.
