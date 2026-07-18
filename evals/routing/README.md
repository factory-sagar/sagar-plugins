# Routing Eval

`cases.json` is the single source of routing expectations. Every case carries a `layer`:

- `layer: "hook"` — decidable by the deterministic intent router
  (`plugins/guardrails/hooks/intent_router.py`). These cases are asserted exactly, in CI,
  on every PR by `plugins/guardrails/tests/test_router_cases_parity.py`. All 39 current
  cases are this layer.
- `layer: "model"` — requires judgment beyond the router's regexes (none today). These run
  only in the live eval: collect model routing decisions into a results file and score with
  `node scripts/eval-routing.mjs --cases evals/routing/cases.json --results <results.json>
  --policy evals/policy.json`.

The router's negative surface is additionally pinned by the 118-prompt noise corpus in
`plugins/guardrails/tests/test_router_noise_corpus.py`: those prompts must never route and
never grant merge/approve authority.

## When to run the live eval

Run the model-layer eval (and re-check thresholds in `policy.json`) when any of these
change:

- router vocabulary or guards in `intent_router.py` beyond what the parity test covers
- the workflow-routing rules in personal or repo `AGENTS.md`
- public workflow skill descriptions (they steer model-side routing when hooks are off)

## Adding a case

Add the case with `layer: "hook"` first; if the parity test cannot pass without weakening
the router's precision (see the noise corpus), retag it `layer: "model"` and leave the
router unchanged. A false injection is worse than a missed one: the four workflows remain
explicitly invocable either way.
