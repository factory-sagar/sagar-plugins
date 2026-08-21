# Golden Task 01: Ambiguous Feature Request

Version: 2

## Target

`grilling` or `tech-spec` Path B.

## Prompt

```text
I want to add a dashboard for our billing system. Spec it out and make it implementation-ready.
```

## Intent

The run exists to turn an underspecified billing-dashboard request into a productive
grill-first conversation rather than an invented implementation-ready design. Success means
surfacing the highest-leverage product or system uncertainty with one focused, recommended
question; asking that question without its recommendation remains partial achievement, while
inventing design details or producing a full implementation-ready specification misses the point.

## Fulfillment

- States that there is not enough context for a full implementation-ready tech spec, or clearly
  identifies the highest-leverage unresolved product/system decision before design.
- Asks exactly one focused question first.
- Provides a recommended answer for that question.
- Keeps the question grounded in product or system intent, such as dashboard users, source data, critical metrics, permissions, or refresh cadence.
- Does not produce a final design until enough answers exist.

## Boundaries

- Invent repository files, API routes, database tables, vendors, chart libraries, or authorization rules.
- Start implementation.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
