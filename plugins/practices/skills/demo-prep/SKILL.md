---
name: demo-prep
version: 1.0.0
description: |
  Get a demo app verifiably ready before showing it: spin it up, smoke-test the critical paths through
  the real UI, verify data and auth state, and record the exact restart command for the demo moment.
  Reads a per-repo demo config when present and offers to create one when absent, so every prep makes
  the next one faster.
  Use when:
  - Preparing a demo app for a customer session ("demo prep", "get the demo ready", "pre-demo check")
  - Verifying a demo app still works after changes, before presenting it
  - Standing up a demo environment and proving the critical paths end to end
tags: [demo, verification, smoke-test, browser, preparation]
---

# Demo Prep

A demo fails in one of three ways: the app won't start, a critical path breaks mid-walkthrough, or the data is in the wrong state. This skill checks all three through the real UI — what the audience will actually see — and leaves you with a one-liner to start the demo cold.

## When to Activate

- The user is about to demo an app to an audience and wants it verified.
- The user asks to "prep", "verify", or "smoke-test" a demo app.
- A demo app changed recently and needs a confidence pass before it's shown again.

## When NOT to Activate

- Mid-feature development verification — that's `verification-loop` (build/lint/test gate).
- Production deploy readiness — that's CI plus `verification-loop`, not a demo walkthrough.
- Debugging a known-broken app — run `debugger` first; come back here once it works.

## Per-Repo Config Convention

Look for `.factory/demo-prep.md` in the repo root. Expected shape:

```markdown
# Demo Prep Config
- Start: <command>            # e.g. pnpm dev
- URL: <local URL with port>  # e.g. http://localhost:3000
- Ready signal: <log line or URL that confirms the server is up>
- Login: <demo account / auth steps, or "none">
- Seed: <data seed command or state expectations, or "none">
- Critical paths:             # ordered, P0 first
  1. <path> — <expected outcome>
  2. ...
- Reset: <how to return to a clean demo state>
- Quirks: <known slow routes, third-party dependencies, fallback notes>
```

- **Config present:** follow it exactly; it encodes everything previous preps learned.
- **Config absent:** discover (package.json scripts, README, AGENTS.md), confirm the critical paths with the user if they're not obvious, run the prep — then **offer to write `.factory/demo-prep.md`** capturing what worked. Every prep should make the next one instant.

## Procedure (follow in order)

**Phase 0 — Preflight.**
- `git status`: confirm the intended branch and a clean (or intentionally dirty) tree; `git log -1` sanity-check that the demoed version is the expected one.
- Check the target port. If a stale server of this app holds it, stop that one process only — never sweep all dev servers on the machine.

**Phase 1 — Start.**
- Launch the dev server in the background. Wait for the ready signal. Capture the URL.
- Startup failure is a hard stop: report it as the P0 blocker; offer to hand it to `debugger`.

**Phase 2 — Smoke the critical paths.**
- Drive each critical path through the browser using the `droid-control` skill (fall back to `agent-browser`/`browser-navigation` only if `droid-control` is unavailable), in config order, P0 first.
- If no browser-automation capability is available at all, **stop and report blocked** — never substitute `curl` checks or claim a smoke pass that didn't happen through the UI.
- At each waypoint: screenshot, check the console for errors, watch for failed network requests.
- A path fails: record it with evidence and move to the next path. Time-to-demo beats completeness of any single investigation.

**Phase 3 — Data and auth.**
- Demo accounts log in. Seed data is present and looks presentable (no test garbage in visible lists). Third-party integrations respond — or their fallback/mock is confirmed working.

**Phase 4 — Report.**
- Pass/fail per critical path with screenshots. Console errors (or "clean"). Blockers ranked P0 (demo-breaking) / P1 (visible wart) / P2 (cosmetic).

**Phase 5 — Leave it demo-ready.**
- Per config: leave the server running and report the URL, or reset state for a cold start.
- Always record the exact **restart one-liner** (command + URL + login) for the demo moment.
- Config file missing or stale? Offer to create/update `.factory/demo-prep.md` now.

## Delegation Map

| Need | Delegate to |
| --- | --- |
| Browser automation for the smoke pass | `droid-control` / browser automation skill |
| A path failed and the cause is unclear | `debugger` (root cause, fix plan) |
| Fix is known and approved | `implementer` |
| "How is this app even put together?" | `quick-analysis`, then `deep-understanding` |
| Long server/setup runs worth offloading | `worker` |

## Anti-Patterns

- Fixing app bugs mid-prep without surfacing them first — report, then fix only if the user opts in. Time-to-demo is the constraint.
- Smoke-testing with `curl` when the demo is a UI. Test what the audience sees.
- Restarting shared infrastructure (databases, tunnels, other apps' servers) to fix one app.
- Skipping the console-error check because the page "looks fine".
- Using real customer data to make a demo prettier. Never.
- Leaving the repo on a surprise branch or with uncommitted changes the presenter doesn't know about.

## Edge Cases

- **Port already in use by the right server:** reuse it, but verify freshness (`git log -1` vs server start time); a stale build demos old behavior.
- **Demo needs realistic data:** synthetic or anonymized only; flag any real-data request.
- **Flaky third-party dependency:** verify the fallback (mock, cached response, talking point) and note it in the report.
- **Multiple demo apps in one session:** prep sequentially, separate reports, separate restart one-liners.
- **Under 10 minutes to demo:** run P0 paths only, report what was skipped.

## Output

Use clean markdown.

# Demo Prep Report

## Status
<ready | ready-with-warts | blocked — one line>

## Config
<`.factory/demo-prep.md` followed | discovered (offer to create config) | created/updated this run>

## Critical Paths
| # | Path | Result | Evidence |
| --- | --- | --- | --- |
| 1 | <path> | pass / fail | <screenshot ref + console state> |

## Blockers
- P0 (demo-breaking): <items or `none`>
- P1 (visible wart): <items or `none`>
- P2 (cosmetic): <items or `none`>

## Restart One-Liner
- Start: `<command>` → <URL> — login: <demo account / none>

## Hand-off
- To `debugger` / `implementer`: <failed paths needing work, else `none`>
- Config file action: <created | updated | offered — user declined | up to date>

## Self-Check

1. Was every critical path exercised through the real UI, with screenshots?
2. Is the console clean — or every error explained in the report?
3. Does the report rank blockers and state pass/fail per path?
4. Is the restart one-liner recorded (command + URL + login)?
5. Did I offer to create or update `.factory/demo-prep.md`?
