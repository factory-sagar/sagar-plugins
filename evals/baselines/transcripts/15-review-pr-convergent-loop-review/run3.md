# Review Outcome

**Mode:** `ship`  
**Tier:** deep, this is broad and high-consequence.  
**Assessment:** **blocked**, no push or merge may occur.

## Required execution sequence

1. Fetch PR metadata, comments, review summaries, conversation, GraphQL thread states, and the live base ref.
2. Run `git rev-list --left-right --count origin/<base>...HEAD`. If behind, run the authorized `git pull origin <base> --rebase`, resolve conflicts safely, rerun full local verification, commit any resulting changes, re-fetch, and prove zero behind.
3. Record the exact synchronized committed range `B0...H0`, changed-path list, untracked-file accounting, selected review lenses, policy evidence, CI-parity matrix, and current validation evidence. The earlier fixes leave no new changes, so retain `H0` and create **no empty commit**.
4. Run the required fresh primary and challenge `change-review` pair in parallel against exactly `B0...H0` (plus `security` if selected). Each native reply must contain complete `Assessment` and `Coverage`.
5. Reconcile the pair's single in-scope finding, apply it, run targeted validation plus a fresh integration gate, and commit the correction as `H1`.
6. Run delta pass 1 on `H0...H1`, with `B0...H1` as context. It finds a distinct in-scope issue; fix, validate, integration-test, and commit as `H2`.
7. Run delta pass 2 on `H1...H2`, with `B0...H2` as context. It finds another distinct in-scope issue; fix, validate, integration-test, and commit as `H3`.
8. Run delta pass 3 on `H2...H3`, with `B0...H3` as context. It finds yet another distinct actionable in-scope issue.

## Required stop condition

The third delta pass exhausts the contract’s three-pass budget. The workflow must stop **before any further edit, review call, commit, push, PR-body update, CI watch, thread resolution, approval, or merge**.

The final newly reported issue remains unmodified and must be reported as the blocker. `reviewedHeadSha` is not established because the latest review is not clean. A new user instruction is required to reset the delta-review budget.

### Deviations

None.
