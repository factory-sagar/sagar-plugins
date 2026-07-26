I've read the governing `security` droid contract and its normative `reviewer-reply-contract.md`, and confirmed the diffed file is not otherwise present in the repo (empty repo, inline diff is the complete post-change state of `src/platform-analytics.ts`). No dependency versions are involved, so no CVE lookups are required. Performing the review inline under the `security` contract.

# Security Review

## Summary
`blocked` — a hardcoded API credential is committed as a silent fallback, and caller-controlled input is concatenated into a SQL string (injection-prone sink).

## Assessment
`blocked`

## Scope Confirmed
- Target: inline unified diff adding new file `src/platform-analytics.ts` (repo has no commits; diff is the full post-change file).
- Surface: 1 file, +18 / −0 lines.
- Assumption (per parent directive): `daysParam` is caller-controlled HTTP query input; the string literal `"statsig-console-fallback-for-local-dev"` is an active credential, not an inert placeholder. This removes reachability/placeholder demotion for both findings.

## Coverage
- Changed files and codepaths:
  - `src/platform-analytics.ts:1` — module-level `STATSIG_TOKEN` with hardcoded literal fallback.
  - `src/platform-analytics.ts:3-11` — `usageOverDays()`: `daysParam` → `Number()` (`:4`) → interpolated into SQL template (`:8`) → executed via injected `runQuery` (`:10`).
  - `src/platform-analytics.ts:13-18` — `fetchGateStatus()`: `gate` interpolated into outbound URL (`:14`), `STATSIG_TOKEN` sent as `Bearer` auth (`:15`), unvalidated `res.json()` (`:17`).
- Security dimensions applied: Injection/SQL (A03) — sink found, arbitrary injection blocked by coercion; Information Disclosure / Secrets handling (A02/A07, CWE-798) — hardcoded credential confirmed; Elevation/Integrity — leaked token enables Statsig gate access; SSRF/Request-tampering — evaluated for `gate`, reachability unconfirmed; DoS — bounded/minor; Crypto/Deserialization/Path-traversal — n/a to this diff.
- Evidence gaps: no caller/route source for `usageOverDays` or `fetchGateStatus` exists in the repo (empty repo); reachability is taken from the parent directive for `daysParam`, and is unconfirmed for `gate`.

## What This Change Touches (security-relevant)
- Trust boundaries crossed: new function consuming HTTP query input into a SQL query; new outbound network egress to `api.statsig.example` carrying a bearer credential.
- Privileged operations involved: database query execution (`runQuery`); authenticated third-party API call (Statsig gates).
- Untrusted input sources introduced: `daysParam` (query string), and `gate` (unknown caller; treated as potentially untrusted).

## Findings (max 8)

- [Critical·High] Hardcoded API credential committed as silent fallback — `src/platform-analytics.ts:1` (consumed at `src/platform-analytics.ts:15`)
  - Why: `const STATSIG_TOKEN = process.env.STATSIG_TOKEN ?? "statsig-console-fallback-for-local-dev";` embeds a literal credential in source. Per the directive this is an active token. Attack path: (1) anyone with read access to the source or built artifact/bundle extracts the token verbatim and calls `https://api.statsig.example/gates/*` as the application (read/modify feature gates → integrity/authorization impact); (2) the `??` fallback fails *open* — in any environment where `STATSIG_TOKEN` is unset (including a misconfigured prod), the app silently authenticates with this known, shared, source-embedded token instead of erroring, so the leaked credential can be the live credential.
  - Impact: Credential disclosure (CWE-798), unauthorized access to the Statsig gates API, and potential feature-flag tampering by any party who reads the repo.
  - Remediation: Remove the literal; fail closed when the env var is absent (`if (!process.env.STATSIG_TOKEN) throw ...`). Rotate/revoke the leaked token since it is now in VCS history. Load secrets from a secret manager and document the required var in `.env.example`.
  - References: CWE-798 Use of Hard-coded Credentials; OWASP A07:2021 Identification & Auth Failures / A02:2021 Cryptographic Failures (secret management).

- [Medium·High] Caller-controlled value concatenated into SQL string (injection sink; currently blocked only by numeric coercion) — `src/platform-analytics.ts:8` (input at `:4`, executed at `:10`)
  - Why: `WHERE day >= DATE_SUB(CURRENT_DATE(), INTERVAL ${days} DAY)` builds SQL by string interpolation of a caller-derived value rather than parameterization (CWE-89 / OWASP A03). Attack path: HTTP `daysParam` → `Number(daysParam)` → `${days}` → `runQuery(sql)`. Honest exploitability as written: `Number()` always yields a numeric primitive / `NaN` / `Infinity`, whose string form contains no SQL metacharacters (no quotes, spaces, semicolons, or comment markers), so classic injection (UNION/stacked/comment) is **not** achievable today — this is why it is not rated Critical. Residual, directly attacker-triggerable behavior: non-numeric input yields `INTERVAL NaN DAY` / `Infinity` (malformed query → errors), and very large values (`days=1e309`, huge integers) produce degenerate/expensive `DATE_SUB` windows. The safety is incidental to a coercion, not a designed control.
  - Impact: Present-day: malformed-query errors / minor resource pressure. Latent: the code is one refactor away from full SQL injection — escalates to [Critical·High] if the `Number()` coercion is removed, if `days` is ever passed as a string, or if this pattern is copied to a non-numeric column/identifier context.
  - Remediation: Use a parameterized/bound query (`... INTERVAL ? DAY` with a bound parameter) or validate to a bounded positive integer (`Number.isInteger` + range clamp) before use; never interpolate request-derived values into SQL text.
  - References: CWE-89 SQL Injection; OWASP A03:2021 Injection.

## Needs Follow-up
- `fetchGateStatus(gate)` at `src/platform-analytics.ts:14`: `gate` is interpolated directly into the outbound URL path. If `gate` is caller-controlled (not evident in this repo), it enables request tampering (path traversal within the host, added query params) and could, in the worst case, misdirect the request carrying the `Bearer` token. Confirm the caller and whether `gate` is user-supplied; if so, allowlist/encode it. Resolution requires the calling code, which is absent from this diff.

## Hand-off
- To `change-review` (correctness, not security): the `NaN`/`Infinity` malformed-query behavior from `Number(daysParam)` is also a plain robustness/correctness bug worth handling.
- To `deep-understanding` (architectural redesign): none.
- Wrong-droid call by parent: no — this is a security review of a diff, correctly scoped to `security`.

## Non-Issues Avoided
- "Critical SQL injection": ruled out as-written because `Number()` coercion prevents any SQL metacharacter from reaching the query; reported instead at calibrated severity with the conditional-escalation note, per the contract's no-over-claiming rule.
- Outbound call uses `https://` — token is not sent in cleartext, so no transport-exposure finding.
- `res.json()` parsing of the Statsig response is not attacker-controlled deserialization; no finding.

## Validation Notes
- Commands run (read-only): `git status --porcelain`, `ls -la`, `ls -la src` (confirmed empty repo; file exists only in the inline diff). No `git show` possible (no commits).
- Package-manager commands: none run (static review only, per contract).
- External lookups (CVE/CWE): none — no dependency/version changes in scope; findings are code-pattern based (CWE-798, CWE-89).
- Caveats: No callers/routes exist in the repo, so `daysParam` reachability is taken from the parent directive and `gate` reachability is unconfirmed (see Needs Follow-up). Line anchors are relative to the new file as introduced by the diff.
