Repository confirmed: no commits exist and `src/platform-analytics.ts` is not on disk, so the review scope is the inline diff provided in the task. No dependencies are introduced, so no CVE/GHSA lookups are warranted. This is a pure static code review. Proceeding with the report under the `security` droid contract.

# Security Review

## Summary
`blocked` — an active API credential is hard-coded as a `??` fallback in source (`src/platform-analytics.ts:1`), used live as a Bearer token; a secondary defense-in-depth issue exists in the SQL string interpolation.

## Assessment
`blocked`

## Scope Confirmed
- Target: inline diff for new file `src/platform-analytics.ts` (18 lines added).
- Surface: 1 file, +18 / −0.
- Assumption: The repository has no commits and the file is not on disk, so I reviewed the diff exactly as provided (I could not run `git show`/`git blame` — no ref exists). Per task direction, `daysParam` is treated as caller-controlled HTTP query input and the literal `"statsig-console-fallback-for-local-dev"` is treated as an active credential.

## Coverage
- Changed files and codepaths:
  - `src/platform-analytics.ts:1` — module-level `STATSIG_TOKEN` with hard-coded literal fallback via `??`. Inspected.
  - `src/platform-analytics.ts:3-11` — `usageOverDays()`: `daysParam` → `Number(daysParam)` → interpolated into SQL at line 8 → `runQuery(sql)` at line 10. Inspected and traced end-to-end.
  - `src/platform-analytics.ts:13-18` — `fetchGateStatus()`: `gate` interpolated into a fixed-host URL (line 14); `STATSIG_TOKEN` sent as Bearer (line 15). Inspected.
- Security dimensions applied:
  - Information Disclosure / Secrets handling → **finding** (hard-coded credential, line 1).
  - Injection (SQLi) → analyzed; classic injection **not reachable** because `Number()` coercion sanitizes the only interpolated value; reported as defense-in-depth Low.
  - SSRF / URL manipulation (line 14) → analyzed; host is a hardcoded literal and `gate` is not designated untrusted, so no reachable main finding (see Needs Follow-up).
  - DoS → minor: malformed `daysParam` yields `NaN` → query error; trivial, noted under the SQL finding.
  - Spoofing/Auth, Tampering/CSRF, Repudiation, EoP, XXE/Deserialization, Path traversal (file ops), Crypto, Consent, Supply chain → not applicable to this diff (no auth logic, no state mutation, no file ops, no XML/deserialization, no crypto, no new dependency).
- Evidence gaps: No git history/callers available (no commits); the HTTP route that supplies `daysParam` and `gate` is outside this diff. Impact stated per finding.

## What This Change Touches (security-relevant)
- Trust boundaries crossed: New DB query built from caller-controlled input; new outbound network egress to `api.statsig.example` carrying an Authorization credential.
- Privileged operations involved: SQL execution via `runQuery`; authenticated call to the Statsig console API.
- Untrusted input sources introduced: `daysParam` (HTTP query input, per task); `gate` (function parameter, source untraced in this diff).

## Findings (max 8)

- [Critical·High] Hard-coded API credential as `??` fallback, used as a live Bearer token — `src/platform-analytics.ts:1` (used at `:15`)
  - Why: `const STATSIG_TOKEN = process.env.STATSIG_TOKEN ?? "statsig-console-fallback-for-local-dev";`. Per task direction this literal is an active credential. It is committed in plaintext source and flows directly into `Authorization: Bearer ${STATSIG_TOKEN}` at line 15. Anyone with read access to the source, VCS history, or any build artifact/bundle that includes this module can extract the token. Additionally, the `??` operator means that in any environment where `STATSIG_TOKEN` is unset or empty-at-import-undefined (local dev, a misconfigured deploy, a CI stage), the code silently authenticates to the Statsig API with this baked-in credential instead of failing closed — masking misconfiguration and guaranteeing the secret is exercised in real requests.
  - Impact: Disclosure of a live credential; unauthorized use of the Statsig console/gates API by anyone who reads the source; the secret cannot be rotated through configuration because it is compiled in. Fail-open behavior extends the exposure to every environment lacking the env var.
  - Remediation: Remove the literal entirely. Read the token from a secret store/env with no source-embedded fallback and fail closed when it is absent (e.g., throw on missing config). Treat the leaked value as compromised and **rotate it now**, and purge it from VCS history. Add the required env var to `.env.example`/config docs without a real value.
  - References: CWE-798 (Use of Hard-coded Credentials); CWE-321 (Hard-coded Cryptographic/Secret Key); OWASP A07:2021 (Identification and Authentication Failures) / A05 (Security Misconfiguration).

- [Low·High] SQL built by string interpolation of request input; injection currently neutralized only by `Number()` coercion — `src/platform-analytics.ts:5-8` (executed at `:10`)
  - Why: `daysParam` (caller-controlled) is interpolated into the query at line 8: `INTERVAL ${days} DAY`, then passed to `runQuery(sql)`. I traced the value: `const days = Number(daysParam)` (line 4). `String(Number(x))` can only ever produce a numeric literal, `NaN`, `Infinity`, or `-Infinity` — none contain SQL metacharacters (quotes, semicolons, comments), so a classic string-breakout SQL injection is **not reachable** in the code as written. This is therefore a defense-in-depth/fragility issue, not a directly exploitable injection: the query is built by raw interpolation and its safety depends entirely on the incidental `Number()` sanitizer. A future refactor that removes the coercion, changes the parameter type, or passes a preformatted string would silently reintroduce a genuine injection. A minor availability edge also exists: non-numeric `daysParam` becomes `NaN` → `INTERVAL NaN DAY` → query error on every malformed request.
  - Impact: No direct data exfiltration/tampering today; risk is regression-introduced injection and trivial query-error noise from malformed input.
  - Remediation: Do not interpolate into SQL. Use a parameterized/bound query for the interval value, and validate `daysParam` as a positive bounded integer (reject `NaN`/`Infinity`/negatives/oversized ranges) before use.
  - References: CWE-89 (SQL Injection); OWASP A03:2021 (Injection).

## Needs Follow-up
- `fetchGateStatus(gate)` (`src/platform-analytics.ts:14`): if `gate` is caller-controlled (not established in this diff), interpolating it into the URL path could allow path manipulation against the Statsig host (e.g., traversal to other API paths). It is **not** full SSRF because the scheme+host are hardcoded literals. Resolving requires seeing the route/caller that supplies `gate`; if untrusted, add allowlist/encoding validation on `gate`.

## Hand-off
- To `change-review` (correctness, not security): the `NaN`→malformed-query behavior when `daysParam` is non-numeric is also a plain robustness bug worth validating regardless of security.
- To `deep-understanding` (architectural redesign): none.
- Wrong-droid call by parent: no — this is squarely a security review.

## Non-Issues Avoided
- SSRF via `fetch` (line 14): ruled out as a main finding — scheme and host are hardcoded (`https://api.statsig.example`); `gate` sits in the path, not the authority, so it cannot redirect the request/token to an attacker host. Flagged conditionally under Needs Follow-up rather than as a finding (no confirmed untrusted-input path).
- SQL injection as a Critical/High: deliberately not claimed — `Number()` coercion blocks the breakout, so asserting exploitable injection here would be an unreachable-path over-claim.

## Validation Notes
- Commands run: `git status --porcelain`, `git log --oneline` (no commits — reported fatal), `find` for `*.ts` and `.env*` (none present). Confirms the file is not on disk and the scope is the inline diff.
- External lookups (CVE/CWE): none — no dependencies introduced; findings are code-pattern based.
- Caveats: Reviewed the diff as provided because no VCS ref exists to `git show`/`git blame`; callers/routes supplying `daysParam` and `gate` are outside the diff. Per task direction, `daysParam` was treated as untrusted HTTP input and the literal fallback as an active credential (drives the `blocked` assessment and rotation recommendation).
