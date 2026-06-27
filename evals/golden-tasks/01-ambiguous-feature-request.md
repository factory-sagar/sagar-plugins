# Golden Task 01: Ambiguous Feature Request

## Target

`grilling` or `tech-spec` Path B.

## Prompt

```text
I want to add a dashboard for our billing system. Spec it out and make it implementation-ready.
```

## Expected behavior

The request is too underspecified for an implementation-ready design. The agent should switch into a grill-first flow instead of inventing product requirements, file paths, schemas, or APIs.

## Must pass

- States that there is not enough context for a full implementation-ready tech spec.
- Asks exactly one focused question first.
- Provides a recommended answer for that question.
- Keeps the question grounded in product or system intent, such as dashboard users, source data, critical metrics, permissions, or refresh cadence.
- Does not produce a final design until enough answers exist.

## Must not do

- Invent repository files, API routes, database tables, vendors, chart libraries, or authorization rules.
- Ask a long questionnaire.
- Start implementation.
- Skip directly to a final `tech-spec`.

## Score

- `pass`: all must-pass assertions are met and no must-not-do assertion appears.
- `partial`: the agent asks one question but omits the recommended answer.
- `fail`: the agent invents design details or writes a full implementation-ready spec.
