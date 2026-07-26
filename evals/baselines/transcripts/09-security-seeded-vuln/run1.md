Scope confirmed: the target file doesn't exist on disk and the repo has no commits, so the review scope is the inline unified diff, which contains the entire new file (`src/platform-analytics.ts`, 18 lines). I've read it in full. No package/CVE lookups are needed (no dependencies in scope). Proceeding with the review under the `security` droid contract.

# Security Review

## Summary
`blocked` — a hard-coded API credential is committed in source (treated as active per task), and the sessions query is assembled by string interpolation of caller-controlled input.

## Assessment
`blocked`

## Scope Confirmed
- Target: inline unified diff adding `src/platform-analytics.ts` (new file, from `/dev/null`).
- Surface: 1 file, +18 / −0 lines.
- Assumption (per task): `daysParam` is untrusted HTTP query input; the literal `STATSIG_TOKEN` fallback is an active credential. `gate` (in `fetchGateStatus`) has no stated trust source → treated as unknown, see Needs Follow-up. Repo has no commits (`git log`: none) and the file is not on disk, so the diff text is the authoritative full post-change content.

## Coverage
- Changed files and codepaths:
  - `src/platform-analytics.ts:1` — module-level `STATSIG_TOKEN` with `??` literal fallback (read in full).
  - `src/platform-analytics.ts:3-11` — `usageOverDays`: `Number()` coercion (`:4`) and SQL template assembly (`:5-9`), executed via `runQuery` (`:10`).
  - `src/platform-analytics.ts:13-18` — `fetchGateStatus`: URL path interpolation (`:14`) + `Authorization: Bearer` header (`:15`).
- Security dimensions applied: **Information Disclosure / Secrets handling** → Critical (hard-coded credential); **Injection (SQL)** → evaluated, breakout not reachable, kept as defense-in-depth; **Spoofing/Auth** → credential reuse via `??` fail-open; **SSRF / Path traversal** → evaluated on `fetchGateStatus`, gated on unknown trust of `gate`; **DoS** → considered on numeric `days`, no meaningful vector; **Repudiation, Crypto, Deserialization, Supply chain, Consent/Privacy** → N/A (no such surface in diff).
- Evidence gaps: trust source of `gate`; whether callers validate inputs upstream; whether `runQuery` supports parameter binding; whether the literal is a genuinely live credential (instructed to assume yes).

## What This Change Touches (security-relevant)
- Trust boundaries crossed: untrusted HTTP query input (`daysParam`) reaches a SQL string builder; outbound authenticated network egress to the Statsig API.
- Privileged operations involved: SQL execution against a `sessions` table; a Bearer-authenticated API call.
- Untrusted input sources introduced: `daysParam` (query param); `gate` (function argument, trust unknown).
- Secrets introduced: `STATSIG_TOKEN` literal fallback embedded in source.

## Findings (max 8)

- [Critical·High] Hard-coded API credential committed in source with fail-open fallback — `src/platform-analytics.ts:1` (used at `src/platform-analytics.ts:15`)
  - Why: `const STATSIG_TOKEN = process.env.STATSIG_TOKEN ?? "statsig-console-fallback-for-local-dev";`. Per task this literal is an active credential. It is committed to the repository (readable by anyone with source or build-artifact access) and is sent verbatim as `Authorization: Bearer ${STATSIG_TOKEN}` at `:15`. The `??` fallback is fail-open: if the env var is unset or rotated in production, requests silently authenticate with the committed token rather than failing loudly. Attack path: any actor with read access to the repo/bundle extracts the token and authenticates to the Statsig API as the application. The `statsig-console` name implies console-scope (elevated) access.
  - Impact: Credential disclosure and unauthorized access to feature-gate configuration (read/modify gates), which can alter application behavior for all users; escalates toward account-level control if the token is console-scoped.
  - Remediation: Remove the literal fallback; require the env var and fail closed at startup if it is missing. Rotate the token now (assume compromised once committed). Source it from a secrets manager. Document it as an empty var in `.env.example`. Add secret scanning to CI to prevent recurrence.
  - References: CWE-798 (Use of Hard-coded Credentials), CWE-259, OWASP A07:2021 (Identification and Authentication Failures), OWASP A05:2021 (Security Misconfiguration).

- [Low·High] SQL assembled by string interpolation of request-derived value (fragile; not currently exploitable) — `src/platform-analytics.ts:8` (assembly `src/platform-analytics.ts:4-9`)
  - Why: `daysParam` (caller-controlled) is interpolated as `... INTERVAL ${days} DAY ...`, the classic SQL-by-concatenation anti-pattern. Reachability of a breakout is currently blocked by `const days = Number(daysParam)` at `:4`: `days` is a JS number, and `${days}` stringifies to only `[-]digits[.digits][e±digits]`, `NaN`, or `Infinity` — none contain SQL metacharacters (quote, `;`, whitespace, comment markers). Any injection payload (e.g. `1 DAY) UNION SELECT secret --`) coerces to `NaN`, yielding `INTERVAL NaN DAY` (a query error), not injected SQL. So this is NOT exploitable SQLi today; it is reported as defense-in-depth because the only guard is incidental stringification.
  - Impact: None currently. It becomes CWE-89 SQL injection (`[High·High]`) the moment `Number()` is removed, `daysParam` is interpolated as a string, or the pattern is copied into a non-coerced context, enabling exfiltration via UNION/subquery against `sessions`.
  - Remediation: Use a parameterized/bound query (extend `runQuery` to accept parameters), or at minimum validate `Number.isInteger(days) && days > 0 && days <= MAX_DAYS` and reject otherwise before building the SQL. Do not rely on `Number()` stringification as the sole control.
  - References: CWE-89, OWASP A03:2021 (Injection).

## Needs Follow-up
- `fetchGateStatus(gate)` — `src/platform-analytics.ts:14` interpolates `gate` into the URL path (`https://api.statsig.example/gates/${gate}`) with the Bearer token attached. The task named only `daysParam` as caller-controlled, so `gate`'s trust source is unconfirmed. If `gate` is caller-controlled, payloads such as `../<other-endpoint>` / encoded `..%2f` traversal, or injected `?`/`#`, could redirect the authenticated request to unintended same-host API endpoints (path manipulation / limited request forgery) with the credential attached. Resolve by confirming whether `gate` is untrusted and validated upstream; if so this is a Medium finding — apply an allowlist and/or `encodeURIComponent(gate)`. (References: CWE-88, CWE-918-adjacent.)
- Credential liveness: the literal reads like a placeholder and `api.statsig.example` is a reserved, non-resolving domain (RFC 2606). If the literal is genuinely not a live credential, Finding 1 downgrades to a fail-open/misconfiguration hardening item. Per the task instruction I treated it as active → Critical.

## Hand-off
- To `change-review` (correctness, not security): the `??` fail-open fallback and negative/`NaN` `days` silently producing wrong-or-erroring analytics are also correctness concerns.
- To `deep-understanding` (architectural redesign): none.
- Wrong-droid call by parent: no — this is an in-scope security review of a bounded diff.

## Non-Issues Avoided
- Direct SQLi breakout via `daysParam`: ruled out at the classic-injection level because `Number()` collapses metacharacters to `NaN` (retained only as a Low defense-in-depth finding, not dismissed).
- `res.json()` at `:17`: standard JSON parsing, no untrusted-code deserialization risk.
- Negative/huge `days` (`-5`, `Infinity`): yields logically wrong or erroring queries, not a security boundary crossing or a meaningful DoS.

## Validation Notes
- Commands run: `LS` on the working directory (only `.git/` and `.factory/` present; no source tree, no commits, so no `git show` target). Static review of the inline diff only.
- External lookups (CVE/CWE): none — no dependencies in scope; CWE/OWASP references are well-known identifiers, not fetched.
- Caveats: The target file is not on disk and the repo has no commits; this review is of the provided diff text, which is the complete new file. No package-manager or scan commands were run, per contract.
