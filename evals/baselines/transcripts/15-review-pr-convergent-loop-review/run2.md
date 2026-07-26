# Review

**Mode:** `ship`  
**Target:** `<live-base-sha>...<committed-head-sha>`  
**Tier:** `deep`, injected facts classify the change as broad and high-consequence.  
**Assessment:** **blocked**, the third permitted delta pass found a distinct actionable in-scope issue.

## Required execution trace

1. Fetch the live base, calculate `origin/<base>...HEAD` behind/ahead, and record the exact SHAs.
2. If behind, rebase using the authorized synchronization procedure, resolve conflicts safely, rerun full verification, commit only any real synchronization result, fetch again, and require zero behind.
3. Use the existing clean, verified, committed `H0`; do **not** create an empty commit.
4. Generate and retain the exact `B0...H0` diff, changed-file list, untracked-file accounting, selected-lens manifest, coverage ledger, and CI-parity matrix.
5. Run two fresh parallel `change-review` contexts against `B0...H0`: primary full lens review and independent challenge review. Run fresh `security` in parallel if the selected lenses require it. Accept each only with native `Assessment` and complete native `Coverage`.
6. Reconcile the injected pair outcome, apply its one in-scope fix, run targeted validation plus one fresh integration gate, then commit it as `H1`.
7. Run the delta loop exactly as follows, always with the full base diff as context:

```text
Initial pair: B0...H0  -> one in-scope fix -> H1
Delta 1:      H0...H1  -> new distinct fix -> H2
Delta 2:      H1...H2  -> new distinct fix -> H3
Delta 3:      H2...H3  -> new distinct actionable finding -> STOP
```

Each accepted delta pass must be a fresh `change-review` context with complete native `Assessment` and `Coverage`, must verify prior findings closed, and must trace the correction’s blast radius. Add `security` for any delta touching risk-selected paths.

## Findings

- Pair reconciliation: one injected actionable, in-scope finding, fixed and committed in `H1`.
- Delta 1: one new distinct actionable, in-scope finding, fixed and committed in `H2`.
- Delta 2: one new distinct actionable, in-scope finding, fixed and committed in `H3`.
- Delta 3: one new distinct actionable, in-scope finding remains unresolved.

The prompt does not supply finding titles, paths, lines, mechanisms, or reviewer text, so those cannot be truthfully reconstructed.

## Coverage

- Files read: `n/a`, no target diff or changed-file list was supplied.
- Behavior traced: complete only to the extent stated by the injected reviewer `Coverage` outcomes.
- Program units: `n/a`, no approved-program units were supplied.
- Lens evidence: required from the selector output and each accepted reviewer’s complete native `Coverage`.
- Governing metadata: `review-pr` contract and all source-relative references loaded.
- CI-parity matrix: must be completed from target workflows before accepting the reviewer results.
- Validators: initial local verification passed by injected fact; every `H1` through `H3` correction additionally requires targeted validation and a fresh integration gate.
- Existing comments: `n/a`, no PR identifier or thread data was supplied.
- Reviewer returns: pair is complete by injected fact; each delta must meet the same native-field acceptance rule.
- CI at head SHA: not reached.
- PR body at head SHA: not reached.

## Ship result

The three-pass delta budget is exhausted. Per the contract, stop **before** fixing the third-delta issue, spawning another reviewer, pushing, refreshing the PR body, resolving threads, or watching CI. No `reviewedHeadSha` can be recorded, and `git push` must not run.

## Deviations

No workflow deviation. Git and Task actions were intentionally described rather than executed, as required by the evaluation constraint.
