---
name: discovering-unknowns
version: 1.1.0
description: |
  Map the gap between the user's request and repository reality. Invoke for unfamiliar
  territory, taste-shaped criteria, blind spots, or worker hand-offs; returns evidence-backed
  unknowns and the shared deviations contract.
tags: [planning, unknowns, blindspot, interview, deviations, map-territory]
user-invocable: false
---

# Discovering Unknowns

The prompt, skills, and context you hand an agent are a **map**. The codebase and its real
constraints are the **territory**. Everything the map gets wrong or leaves out is an
**unknown**, and unknowns are where long-horizon work goes wrong: too specific a map and the
agent follows the plan off a cliff; too vague and it fills gaps with industry defaults that
don't fit this repo.

The failure is rarely the model. Post-merge reverts and re-lands, and after-the-fact PRs
fixing stale doc claims, are the expensive form of unknowns discovered late. Every technique
here is a cheap way to find them early. Keep determinism where it belongs — in contracts
(output shapes, gates, invariants) — and use these techniques to make sure the contract is
the *right* one before execution. Paths stay free; contracts stay fixed.

## The 2x2

| | Known | Unknown |
| --- | --- | --- |
| **Known** | What the prompt says. Keep it evidence-anchored. | What you know you haven't decided. → Interview |
| **Unknown** | Taste: you'd recognize it, but would never write it down. → Brainstorm and react | What you haven't considered at all. → Blind-spot pass |

Two habits raise every technique's yield:

- **Disclose your starting point.** Tell the agent where you are in your thinking, your
  familiarity with the area, and what you have already tried. Questions calibrate to the
  gap, not to a generic audience.
- **Prefer source code as a reference.** When you cannot articulate what you want, point at
  code that already does it — a vendored library, a sibling module, another language is
  fine — and say what to look for. Code carries more constraint detail than any description.

## When to Activate

- Starting work in a part of the codebase (or a domain) the operator does not know well.
- The acceptance criteria are taste-shaped: "I'll know it when I see it."
- The user says "blindspot pass", "unknown unknowns", "what am I missing", "help me prompt better".
- A plan is about to be delegated for implementation (attach the Deviations contract below).
- A large change is done and the operator wants a comprehension check before merge.

## When NOT to Activate

- The change is small and the operator already knows the territory — go straight to `spec`
  or implementation.
- The unknowns are the *model's*, not the operator's (a droid missing repo context needs a
  better prompt or an investigation droid, not this skill).
- A full interview session is warranted — that is `grilling`; this skill's interview pattern
  is for 1-3 targeted questions inline.

## Techniques

### 1. Blind-spot pass (before scoping)

Enumerate the operator's unknown unknowns in the target area, from repo evidence — not a
generic checklist. Search first, then report:

- **Territory constraints**: existing modules, middleware, config flags, and gates the work
  must pass through (cite `file:line`).
- **Conventions that will bind the change**: the patterns neighboring code follows, doc
  contracts (`AGENTS.md`-style machine-readable claims), CI gates and ratchet baselines the
  diff will trip.
- **Historical decisions**: prior attempts, reverts, TODOs, and comments that explain why
  the obvious approach was not taken.
- **Calibration**: what "good" looks like here — the strongest existing example of the same
  kind of work in this repo.

End with the 2-4 questions whose answers would most change the approach, ordered by how much
architecture hangs on each. Do not start implementing.

> "I'm adding a new auth provider but I know nothing about the auth modules in this codebase.
> Do a blindspot pass: my unknown unknowns, with file:line evidence, then the questions I
> should be answering before I prompt you to build."

### 2. Interview (for known unknowns)

One question at a time, highest-leverage first: prioritize questions where the answer would
change the architecture, and include a recommended answer with each. For a full session, use
the `grilling` skill; inline, ask at most 3 via `AskUser`. Record answers as resolved
decisions in the spec — an interview whose answers stay in chat is an unknown deferred, not
resolved.

### 3. Brainstorm and react (for taste)

When criteria are recognize-on-sight, produce **variants to react to** before wiring
anything: 3-4 genuinely different directions (not one direction at 4 volumes), cheapest to
most ambitious, each with a one-line tradeoff. For UI, a throwaway HTML mock with fake data
beats a description; for APIs and data models, show the contending type signatures side by
side. React, pick, discard the rest — finding an unknown known during prototyping is cheap;
finding it during implementation costs a revert.

### 4. Plan for review, decisions first

When presenting an implementation plan, lead with the decisions the operator is most likely
to change — data-model changes, new type contracts, anything user-facing — and bury the
mechanical refactoring at the bottom. A plan ordered by file path hides the two decisions
that actually needed review.

### 5. Deviations contract (during implementation)

No amount of planning removes all unknowns; the territory will contradict the map
mid-implementation. Whoever implements (worker, droid, or the main agent) carries this
standing rule:

- **Minor contradiction** (a detail is wrong; the goal stands): take the **conservative
  option** — the one that adds no unrequested product surface and is easiest to revert —
  log it, and keep going.
- **Premise contradiction** (the evidence says this approach is wrong): **stop and report**
  with evidence and a proposed alternative. Do not push through, and do not silently pivot.

Log format (in the report, or an `implementation-notes.md` for long units):

```md
## Deviations
- D1 — plan: <what the plan/finding/spec said>
  territory: <what the code actually showed — file:line evidence>
  chose: <the conservative option taken>
  impact: <behavior/scope effect, one line>
```

If none: `Deviations: none.` The log is not overhead — it feeds `pr-describer` (deviations
become reviewer-facing notes), keeps doc contracts honest in-flight instead of via follow-up
fix PRs, and is the raw material for the next plan's blind-spot pass.

### 6. Quiz gate (after implementation, optional)

After a long session, the agent has usually done more than the operator absorbed, and a diff
read only shows surface. Offer a short quiz — 3-5 questions on behavior, edge cases, and
what would break if a dependency changed — and treat a wrong answer as a signal to re-read
before push, not as a formality. Offer it; never force it.

## Wiring

| Moment | Use | Consumed by |
| --- | --- | --- |
| Before `spec` in unfamiliar territory | Blind-spot pass | `spec` Phase 1-2 anchor |
| Requirements fuzzy after brainstorm | Interview (full session → `grilling`) | spec's resolved decisions |
| Taste-shaped criteria | Brainstorm and react | `tech-spec` alternatives |
| Handing a unit to `implementer` / `worker` | Deviations contract in the prompt | report's `## Deviations` |
| `tdd-workflow` Step 4, `review-pr` fix mode | Deviations contract | `pr-describer` Notes for Reviewers |
| Before push/merge of a long session | Quiz gate (on request only — not part of the standard loop) | operator confidence |

Long-horizon models (the Fable-class tier) raise the ceiling on all of this: the more work
one prompt buys, the more unknowns it will cross, so the bottleneck moves to how well the
operator surfaced unknowns — which is exactly this skill's job. Run it at the orchestrator
level; the delegated droids keep their pinned models.

## Anti-Patterns

- Running a blind-spot pass as a generic checklist with no `file:line` evidence.
- Asking ten questions at once. One at a time, architecture-changing first.
- Prototyping four volumes of the same direction and calling it a brainstorm.
- Logging a premise contradiction as a deviation and pushing through — that is a stop-and-report.
- Silent pivots: any departure from the plan that appears nowhere in the report.
- Treating the quiz as a rubber stamp — if the operator fails it, that is information.
- Using this skill to stall obvious work. Small change + known territory = just build it.

## Self-Check (before returning)

1. Did every blind-spot claim cite repo evidence rather than general knowledge?
2. Are the closing questions ordered by architectural leverage?
3. If work was delegated, did the prompt include the Deviations contract verbatim?
4. Are all deviations logged with plan/territory/chose/impact — and were any of them
   actually premise contradictions that should have stopped the work?
5. Did resolved answers land in the spec/plan, not just the chat?
