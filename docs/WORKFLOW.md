# Workflow

A disciplined loop from idea to merged change. Each stage has one entry point, the work
between stages is owned by skills and droids, and a human message mid-flow is either a
decision or a defect report.

## The loop

```
IDEA
  │
  ▼
1. PLAN        /spec <request, constraints, non-goals>
  │            spec clarifies (≤1 question), delegates to the planner droid,
  │            returns a decisions-first plan with pre-answered open questions
  │            YOU: react to Decisions + Open Questions, approve      ← gate 1
  ▼
2. BUILD       /implement U<n>   (independent units in parallel)
  │            approved change set → implementer · new behavior → tdd-workflow
  │            every path carries the Deviations contract
  ▼
3. GATE        /review-fix <target>
  │            existing PR threads fetched first and triaged as findings,
  │            change-review ∥ security reviews, fixes applied, verified,
  │            committed locally — STOPS
  │            YOU: "push"                                            ← gate 2
  ▼
4. LAND        /ship  (or just "push")
  │            commit → push → PR body per repo template → CI watch →
  │            debugger on non-obvious failures → threads resolved →
  │            merge-ready report
  ▼
5. MERGE       "merge it"
               executes only with green CI + zero unresolved review threads,
               verified against the live API                          ← gate 3

LATER          /fix-pr <PR> — review comments arrived on an open PR:
               triage every one, fix, reply, resolve, CI green
```

## Entry points

| Intent | Type | What happens without further prompting |
| --- | --- | --- |
| Scope new work | `/spec <request>` | Clarify → `planner`: territory scan with evidence, decisions with rejected alternatives, agent-sized units, sequencing, open questions with recommended answers |
| Build a unit | `/implement U<n>` | Routes to `implementer` / `tdd-workflow` / inline; Deviations contract; verification |
| Review + fix | `/review-fix <PR\|branch\|staged>` | Thread triage + parallel reviews + fixes + local commit; stops before push |
| Land it | `push` or `/ship` | Commit, push, templated PR body, CI watch loop, thread resolution, merge-ready report |
| Late comments | `/fix-pr <PR>` | Full comment triage, fix, reply, resolve, CI green, approve/done |
| Merge | `merge it` | Hard-gated: explicit instruction + green CI + zero unresolved threads (live re-fetch) |

## Stop typing these

Each of these chores has exactly one owner in the loop. Needing to type one mid-flow means
a contract broke — treat it as a defect and fix the skill, not the symptom:

`monitor ci` · `why is ci failing` · `fix the PR body` · `resolve comments` ·
`push and update PR` · `make sure everything passes` · `continue` / `proceed`
