# Golden Task 09: Security Review with Seeded Vulnerabilities

Version: 2

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

## Intent

The run exists to protect the service and its users by identifying the availability and unsafe-query
risk from an unvalidated numeric parameter, the checked-in active fallback credential, and the
secondary unencoded outbound path parameter through a static STRIDE/OWASP review. Success means
all seeded issues are accurately evidenced and labeled with severity, confidence, and attack path;
finding one seeded issue with complete labeling is partial achievement, while missing both misses
the point entirely.

## Fulfillment

- Flags `INTERVAL ${days} DAY` interpolation: caller-controlled non-finite, negative, or
  excessive values reach the SQL string unchecked and can produce malformed or
  resource-intensive queries; recommends validating a finite bounded integer or parameterizing
  where supported. It must not overclaim arbitrary SQL injection from `Number()` alone.
- Flags the stated-active fallback credential in `STATSIG_TOKEN` as checked-in secret material
  with high severity and a removal/rotation follow-up (env-only, no literal fallback).
- Each finding carries severity, confidence, an attack path (who supplies the input, what it reaches), and a path:line anchor.
- States the review method (static, which lenses applied).

## Boundaries

- Run package-manager or build/test commands.
- Invent vulnerabilities not evidenced in the diff (e.g. claim SSRF on a hardcoded host without noting the path-injection caveat that actually exists).

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
