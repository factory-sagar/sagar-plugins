Confirmed scope: the repository has no commits and only `.factory`/`.git` exist, so `src/platform-analytics.ts` lives solely in the provided diff. There are no in-repo callers to trace; I apply the two trust premises the task fixed (caller-controlled `daysParam`, active credential fallback) and review the diff in full under the `security` contract.

# Security Review

## Summary
`blocked` — a hard-coded API credential is committed in the diff and used as a live Bearer token; a secondary unvalidated-input-into-dynamic-SQL issue also needs fixing.

## Assessment
`blocked` (secret present in diff → P0 per contract edge case; rotation required in addition to removal)

## Scope Confirmed
- Target: provided diff adding new file `src/platform-analytics.ts` (18 lines).
- Surface: 1 file, +18 / −0.
- Assumption: per task, `daysParam` is caller-controlled HTTP query input and the fallback string is an active credential. Repo has no commits and no callers, so route/middleware/auth context outside the file is unavailable; I review the file as the entire scope.

## Coverage
- Changed files and codepaths:
  - `src/platform-analytics.ts:1` — module-level `STATSIG_TOKEN` with literal fallback.
  - `src/platform-analytics.ts:4,8` — `Number(daysParam)` coercion and `${days}` interpolation into the `sessions` query; executed via `runQuery` at `:10`.
  - `src/platform-analytics.ts:14-16` — `fetchGateStatus` builds an outbound URL from `gate` and attaches the bearer token.
- Security dimensions applied:
  - Information Disclosure / Secrets handling → Finding 1 (hard-coded credential).
  - Injection (SQL) + Improper Input Validation + DoS → Finding 2 (direct string SQLi ruled out; residual validation/DoS issue kept).
  - SSRF / Path traversal on outbound fetch → Needs Follow-up (trust of `gate` unstated).
  - Spoofing/AuthN, EoP → not applicable at this layer (library functions; auth expected at the route layer, not in scope).
- Evidence gaps: no caller/route context (empty repo); trust status of `fetchGateStatus`'s `gate` argument is not specified by the task.

## What This Change Touches (security-relevant)
- Trust boundaries crossed: caller-controlled query input reaching a SQL string; module-level secret read; new network egress carrying a credential.
- Privileged operations involved: database query execution (`runQuery`); authenticated HTTP call to the Statsig console API.
- Untrusted input sources introduced: `daysParam` (confirmed untrusted per task); `gate` (trust unconfirmed).

## Findings (max 8)

- [Critical·High] Hard-coded credential fallback shipped in source and used as a live Bearer token — `src/platform-analytics.ts:1` (used at `:15`)
  - Why: `const STATSIG_TOKEN = process.env.STATSIG_TOKEN ?? "statsig-console-fallback-for-local-dev";`. Per the task premise this literal is an active credential. It is committed to source (and git history), and `fetchGateStatus` sends it verbatim as `Authorization: Bearer ${STATSIG_TOKEN}`. Attack path: anyone with read access to the repo or its history (internal dev, leaked clone, dependency-of-a-dependency mirror, CI logs) reads the token and calls `https://api.statsig.example/gates/*` as this service. The `??` fallback compounds the risk: if `STATSIG_TOKEN` is ever unset in a real environment, the app silently falls back to the baked-in credential instead of failing closed, so a production misconfiguration is masked and the shared secret is exercised against the live API.
  - Impact: credential compromise → read/tamper of feature-gate configuration (Information Disclosure + Tampering, and Elevation if gates guard privileged behavior). Because the secret is in version control, it must be treated as already leaked.
  - Remediation: remove the literal entirely; require the env var and fail closed when missing (e.g., throw on startup if `!process.env.STATSIG_TOKEN`). Rotate/revoke the exposed token now, and scrub it from history. Load secrets from a secret manager; document the required env var in `.env.example` without a real value.
  - References: CWE-798 (Use of Hard-coded Credentials), CWE-321 (Hard-coded Cryptographic Key), OWASP A07:2021 / A05:2021.

- [Medium·High] Caller-controlled value interpolated into dynamically built SQL without validation — `src/platform-analytics.ts:4,8` (executed at `:10`)
  - Why: the query is assembled by string interpolation (`INTERVAL ${days} DAY`) rather than parameterization. I verified the direct/classic SQL-injection path is **not** exploitable here: `days = Number(daysParam)` always yields a JS `number`, and number-to-string conversion can only emit digits, `.`, `-`, `e`, or the bare tokens `NaN`/`Infinity` — none of which carry SQL metacharacters (a payload like `1); DROP TABLE sessions;--` coerces to `NaN`). So I am **not** claiming injection. The real, reachable issue is missing input validation: `Number()` does not constrain sign, range, integrality, or finiteness, and the unvalidated result flows straight into the executed query. `daysParam = "NaN"`/non-numeric → `INTERVAL NaN DAY` (query error → potential error-based information disclosure if DB errors propagate to the response); negative/huge/fractional values (e.g. `-99999`, `1e15`) → semantically wrong or expensive scans (logic manipulation / DoS). The interpolation pattern is also fragile: a later refactor that drops `Number()` or interpolates `${daysParam}` directly turns this into a direct SQLi.
  - Impact: query errors and possible error-message disclosure; wrong results / resource-heavy scans as a low-cost DoS. Limited blast radius because injection is currently neutralized (hence Medium, not High). The DoS/error consequence is inferred from typical SQL-engine behavior; the presence of unvalidated attacker input reaching the executed query is certain (hence High confidence in the finding).
  - Remediation: parameterize (`INTERVAL ? DAY` with a bound parameter) and validate before use — reject unless `Number.isInteger(days) && days > 0 && days <= <sane max>`. Do not build SQL by interpolation even for numerics.
  - References: CWE-20 (Improper Input Validation), CWE-89 (SQL Injection — pattern to eliminate), OWASP A03:2021.

## Needs Follow-up
- `fetchGateStatus` outbound URL built from `gate` — `src/platform-analytics.ts:14`. `gate` is interpolated into the request path with no encoding or allowlist, and the request carries the bearer token. If `gate` turns out to be attacker-controlled (task did not state), a value like `../../admin/...` normalizes within the fixed host and sends the credential to an unintended endpoint (path-traversal-style abuse; limited SSRF since the authority `api.statsig.example` cannot be swapped via the path). Resolve by confirming the trust source of `gate`; if it can be caller-influenced, `encodeURIComponent(gate)` and validate against an allowlist of gate names. Confidence that this is a vulnerability is `unconfirmed` pending the trust status of `gate`.

## Hand-off
- To `change-review` (correctness, not security): the `Number()` coercion silently accepting `NaN`/negatives is also a plain correctness/robustness concern.
- To `deep-understanding` (architectural redesign): none.
- Wrong-droid call by parent: no — this is squarely a security review.

## Non-Issues Avoided
- Direct string SQL injection via `daysParam`: ruled out — `Number()` coercion collapses any metacharacter payload to a numeric/`NaN`/`Infinity` value that cannot break the query's syntax. The residual, real issue (missing validation → DoS/error) is kept as Finding 2 rather than overstated as injection.
- Token exfiltration to an attacker host via `gate`: ruled out — the host is fixed in the template and the `@`/authority trick cannot relocate it through the path; only same-host path abuse remains, captured under Needs Follow-up.

## Validation Notes
- Commands run (read-only): `LS` on repo root, `Grep` for the new symbols. Repo has no commits; `src/platform-analytics.ts` exists only in the supplied diff, so there is no post-change file on disk or caller graph to trace.
- External lookups (CVE/CWE): none — no dependency change to verify; findings are code-level.
- Caveats: no route/auth context available (empty repo); severity of Finding 2's DoS/error impact and the entire `gate` follow-up depend on runtime/DB behavior and the (unstated) trust source of `gate`. Static review only; no package or scan commands executed, per the contract.
