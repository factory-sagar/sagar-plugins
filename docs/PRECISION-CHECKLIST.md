# Precision Checklist

The per-file standard for every prompt surface in this repository (droids, skills,
supporting docs, READMEs, hooks). A file passes when every item holds. Applied fleet-wide
once; apply to any file you touch afterward.

## Frontmatter (droids and skills)

- [ ] `name` matches the filename (droids) or directory (skills).
- [ ] `description` is within budget (500 droid / 320 skill), states when to invoke, and
      matches what the body actually does.
- [ ] `model` + `reasoningEffort` are pinned, valid for the model, and identical in
      `evals/model-assignments.json` and every doc table that names them (CI-enforced).
- [ ] `tools` is the minimum the role needs; read-only roles carry no edit/execute tools.

## Claims

- [ ] Every factual claim is currently true: counts, paths, commands, model names, hook
      behavior, CI behavior.
- [ ] Anything mechanically checkable is checked by `scripts/validate.mjs`,
      `scripts/validate-evals.mjs`, or a test, not by trust.
- [ ] Anything not mechanically checkable points at its source instead of restating it
      (the reviewer-reply-contract pattern: one normative home, pointers elsewhere).

## Contracts

- [ ] Droids declare `## Output` and the body produces exactly that shape.
- [ ] Every cross-file handoff names the same fields on both sides (producer and consumer).
- [ ] Templates the agent must emit are never polluted with meta-guidance; pointers live in
      prose sections only.

## Determinism language

- [ ] Instructions an agent must branch on are decidable: "do X when Y; otherwise Z", never
      "consider" / "may want to".
- [ ] Authority-bearing words (approve, merge, land, ship, push) appear only with their
      exact preconditions.
- [ ] Retry/budget rules state their exact counts and what exhausts them.

## Consistency

- [ ] One canonical term per concept: `unit`, `program head`, `final head`, `review thread`,
      `blocked`, `delivery gate`.
- [ ] One normative definition per policy; restatements carry an on-conflict pointer.
- [ ] No rule here contradicts `docs/WORKFLOW.md`, the hooks' actual behavior, or the
      standing rules in `AGENTS.md`; when hook behavior changes, the prose that describes it
      changes in the same PR.
