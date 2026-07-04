# Trial: implementer model A/B — gpt-5.5 vs claude-fable-5 (2026-07-04)

**Decision: ADOPT `claude-fable-5` (xhigh) for `implementer`.** Fallback pin: `gpt-5.5` (xhigh).

## Protocol

Spec-approved threshold: adopt only if fable strictly wins golden 08, or ties at pass AND wins
the real unit on >=2 of {minimality, deviations quality, verification rigor} with none worse.
Ties keep gpt-5.5 (half the cost).

Both legs ran **in-session via the Task tool** — A on the installed `implementer`, B on a
temporary `.factory/droids/implementer-fable.md` variant — against isolated scratch dirs
(golden 08) and isolated factory-internal worktrees (real unit: the PR 344 factory-droid P1,
clamp GET /attempts `limit` to 1..200). Identical prompts modulo working directory. Both
real-unit diffs were independently verdicted by `change-review`.

## Results

| Leg | A: gpt-5.5 | B: claude-fable-5 |
| --- | --- | --- |
| Golden 08 verdict | pass (attempt 1 completed the edit but returned no report; retry passed) | pass, first attempt |
| Golden verification | git diff/status only; "manual trace" asserted, not executed | executed 9-input runtime trace in a throwaway copy |
| Golden deviations | logged `none` despite making the same non-finite-fallback judgment call B logged (silent deviation) | D1 logged with plan/territory/chose/impact |
| Real unit review | `correct`, no findings | `correct`, no findings |
| Convention fit | inline clamp, reviewer suggestion verbatim | schema-transform clamp matching sibling routes (audit-logs, promotions) |
| Verification | 1 test file + typecheck + lint | 95-test domain suite + eslint --max-warnings=0 + prettier + typecheck |
| Tests added | 3 clamp cases | 4 clamp cases incl. non-numeric -> default 50 |
| Territory insight | none | found sibling fractional-limit gap (no trunc in audit-logs/promotions clamps) — confirmed independently by the reviewer; surfaced, correctly not fixed |

Rule application: goldens tie at pass -> real unit decides -> B wins deviations quality and
verification rigor, ties minimality with none worse -> adopt.

## Caveats

- n=1 real unit, n=1 valid golden pair. A's lost report may have been plumbing; counted as a
  reliability note, not decisive evidence.
- Cost: fable bills 4x vs 2x. The convention-fit and adjacent-bug value on the real unit is
  the justification; revisit if quality regresses or pricing shifts.

## Harness learning (already folded into docs)

`droid exec` has no Task tool, so the runner cannot exercise pinned droids: the first
exec-based "A/B" produced two transcripts both authored by the exec session model, and the
strict real-unit exec run correctly refused ("Task tool is not available"). Droid model A/Bs
must run in-session; `run-golden-task.sh --droid` is documented accordingly.

## Artifacts

- Local (not committed): `~/code/factory/ab-trial/` — prompts, run logs, evidence diffs,
  including `evidence/attempts-clamp-schema-level.patch` (B's real-unit fix, applicable to
  PR 344's open bot comment).
- Session IDs: golden A attempt 1 `39e0db05` (empty return), golden A retry `8f616088`,
  golden B `cba49b1f`, real A `39ff7482`, real B `7a4dfb88`, review A `f7d6b56f`,
  review B `319af69c`, doc apply `c5ebacfa`.
- Invalid exec-based golden runs (contract-adherence only, not model evidence):
  `evals/runs/20260704T031802Z-08-implementer-minimal-fix-{a-gpt55,b-fable}/` (local).
