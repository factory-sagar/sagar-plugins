---
description: Implement a task - route to the implementer droid or tdd-workflow, carry the Deviations contract, verify
disable-model-invocation: true
---

Implement: $ARGUMENTS

Route by what is in hand:
1. An approved change set exists (review findings, a spec unit with acceptance criteria, a debugger fix plan, an explicit fix list) - delegate to the `implementer` droid with the change set
2. New or changed behavior without an approved change set - run the tdd-workflow skill (RED -> GREEN -> REFACTOR with checkpoint commits)
3. Small mechanical change in known territory - apply it inline

In every path, carry the Deviations contract from the discovering-unknowns skill: minor territory contradiction -> conservative option + logged deviation; premise contradiction -> stop and report. Never deviate silently.

Finish with the verification-loop skill (or the repo's master gate) and report deviations alongside the changes.

If no task is provided, ask for one.
