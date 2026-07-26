I've read the governing `security` droid contract and verified the environment: the repo has no commits and `src/platform-analytics.ts` does not exist on disk, so I'm reviewing the inline diff text as the authoritative scope. This is a small diff (1 file, no dependencies), so a full static review applies. No CVE lookups are needed (no dependencies changed). Performing the review inline under the contract now.

# Security Review

## Summary
`blocked` — a hard-coded Statsig API credential is committed as a fallback, and request-derived input is concatenated into raw SQL.

## Assessment
`blocked`

## Scope Confirmed
- Target: inline diff for new file `src/platform-analytics.ts` (provided in task).
- Surface: 1 file, +19 / −0.
- Assumption: The file is not present in the working tree (`git` has no commits; `Glob`/`ls` confirm no `src/`), so I review the diff text as authoritative. Per task framing, `daysParam` is caller-controlled HTTP query input and the literal token fallback is an active credential. `gate` is an exported function parameter whose caller I cannot see, so I trace it as potentially caller-influenced.

## Coverage
- Changed files and codepaths:
  - `platform-analytics.ts:1` — module-level `STATSIG_TOKEN` with hard-coded fallback string.
  - `platform-analytics.ts:3-11` — `usageOverDays()`: `Number(daysParam)` → interpolated into raw SQL at `:8`, passed to `runQuery`.
  - `platform-analytics.ts:13-18` — `fetchGateStatus()`: `gate` interpolated into request URL at `:14`; token sent in `Authorization` header at `:15`.
- Security dimensions applied:
  - Information Disclosure / Secrets handling → **hit** (hard-coded credential, line 1).
  - Injection (SQL) → **partial**: raw string SQL construction; classic breakout blocked by `Number()`, reachable error/DoS remains.
  - SSRF / Path injection → **partial**: `gate` not URL-encoded; host is fixed so cross-host SSRF not reachable, same-host path/param manipulation possible.
  - DoS → minor (unvalidated numeric input; no fetch timeout).
  - Auth/Spoofing, Tampering(CSRF), Repudiation, Crypto, Path traversal(fs), Deserialization, Supply chain → not applicable to this diff.
- Evidence gaps: `runQuery` DB driver and `fetchGateStatus` callers are outside the diff; noted in each finding and Needs Follow-up.

## What This Change Touches (security-relevant)
- Trust boundaries crossed: new HTTP-query-derived input reaching a SQL string; new outbound network egress to `api.statsig.example` carrying a bearer credential.
- Privileged operations involved: database query execution; authenticated call to an external feature-gate API.
- Untrusted input sources introduced: `daysParam` (SQL), `gate` (outbound URL path).

## Findings (max 8)

- **[Critical·High] Hard-coded Statsig API credential committed as fallback — `src/platform-analytics.ts:1`**
  - Why: `const STATSIG_TOKEN = process.env.STATSIG_TOKEN ?? "statsig-console-fallback-for-local-dev";`. The literal (treated as an active credential per the task) is embedded in source and used as a live `Bearer` token at `:15`. Attack path: (1) anyone with repository read access (or the built/bundled artifact, if this module is ever bundled) reads a working token directly from source control — no exploitation required; (2) in any environment where `STATSIG_TOKEN` is unset (misconfig, local/staging drift), the app silently falls back to this known token and authenticates to `api.statsig.example` with it. The name `statsig-console-*` suggests a Console/management-tier key, which can enumerate and mutate feature gates.
  - Impact: credential compromise and unauthorized Statsig API access; if the key is management-scoped, tampering with feature gates (integrity / elevation over flag-controlled behavior). Secret is also exposed in git history the moment it is committed.
  - Remediation: remove the fallback entirely; read `process.env.STATSIG_TOKEN` and fail closed (throw at startup) when missing; **rotate the exposed token immediately** and move it to a secret manager; add `STATSIG_TOKEN=` as an empty placeholder in `.env.example` (never a real value). Purge from history if committed.
  - References: CWE-798 (Use of Hard-coded Credentials), CWE-321 (Hard-coded Cryptographic Key), OWASP A07:2021 Identification & Authentication Failures / Secrets Management.

- **[Medium·Medium] Request-derived input concatenated into raw SQL — `src/platform-analytics.ts:8` (context 4-10)**
  - Why: The query is assembled by string interpolation — `... INTERVAL ${days} DAY ...` — with `days` derived from caller-controlled `daysParam` (`:4`). Reachability analysis: `Number(daysParam)` coerces to a numeric primitive (or `NaN`/`Infinity`), so a metacharacter breakout (`'; DROP …`) is **not currently reachable** — I am explicitly not calling this a live breakout SQLi. Two real problems remain: (a) the raw-string construction is the SQL-injection anti-pattern and is one refactor away from exploitable (e.g., switching to `parseInt` on a partly-numeric string, or interpolating a second string field); (b) attacker-triggerable error/DoS: `daysParam=abc` → `NaN`, `daysParam=1e999` → `Infinity`, producing `INTERVAL NaN DAY` / malformed SQL and query errors on demand. The unresolved assumption (hence Medium confidence) is `runQuery`'s driver behavior, which is outside the diff.
  - Impact: repeatable query failures (error-based DoS / error surface today); latent SQL injection if the coercion is ever weakened.
  - Remediation: use a parameterized/bound query for the interval (`INTERVAL ? DAY` with a bound param) and validate the input as a bounded positive integer: `if (!Number.isInteger(days) || days < 1 || days > 365) throw …`.
  - References: CWE-89 (SQL Injection), CWE-20 (Improper Input Validation), OWASP A03:2021 Injection.

- **[Low·Medium] `gate` interpolated into outbound URL without encoding — `src/platform-analytics.ts:14`**
  - Why: `fetch(\`https://api.statsig.example/gates/${gate}\`, …)` inserts `gate` into the URL path with no `encodeURIComponent`. Cross-host SSRF is **not reachable** (scheme + host are fixed literals; a `@` in the path stays in the path, not the authority). However, if `gate` is caller-influenced, unencoded `../`, `?`, or `#` allow same-host path/query manipulation (e.g., `gate="../admin/keys"` normalizes to `/admin/keys`), causing the request — and the attached `Bearer` credential — to hit unintended endpoints on the trusted host.
  - Impact: request redirection within the trusted API surface with the bearer token attached; scope depends on the unseen caller (hence Medium confidence).
  - Remediation: `encodeURIComponent(gate)` and validate `gate` against an allowlist / expected format; consider constructing via the `URL` API.
  - References: CWE-88 / CWE-20, OWASP A10:2021 SSRF (adjacent).

## Needs Follow-up
- `runQuery` implementation / DB driver: confirms whether the driver ever treats numeric-string interpolation specially and lets Finding 2's severity be finalized. Resolve by reading the query layer.
- `fetchGateStatus` callers: whether `gate` is reachable from untrusted input determines whether Finding 3 rises above Low. Resolve by tracing routes/callers.

## Hand-off
- To `change-review` (correctness, not security): `res.json()` at `:17` is called without checking `res.ok` (non-2xx bodies parsed as data); `fetch` has no timeout/abort. Non-security correctness/robustness.
- To `deep-understanding` (architectural redesign): none.
- Wrong-droid call by parent: no — this is a security review of a diff, correctly scoped to `security`.

## Non-Issues Avoided
- Classic breakout SQL injection via `daysParam`: ruled out as a live High finding because `Number()` yields a numeric primitive (or `NaN`/`Infinity`) before interpolation, so SQL metacharacters cannot survive — reported instead as pattern-risk + error DoS (Finding 2).
- Cross-host SSRF / token exfiltration via `gate`: ruled out because scheme and host are fixed literals; only same-host path/query manipulation remains (Finding 3).

## Validation Notes
- Commands run: `git status --porcelain`, `ls -la`, `Glob` for `src/**` and `platform-analytics.ts` (all confirm the file is not on disk; diff text used as scope). No package-manager, build, or write commands executed (static review only, per contract).
- External lookups (CVE/CWE): none (no dependencies changed; CWE/OWASP identifiers cited from knowledge).
- Caveats: `runQuery` and `fetchGateStatus` callers are outside the provided diff; findings state their reachability assumptions explicitly.
