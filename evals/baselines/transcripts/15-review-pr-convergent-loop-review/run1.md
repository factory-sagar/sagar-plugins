# Contract Result

**Mode:** `ship`  
**Outcome:** **blocked**, nothing may be pushed.

Git and Task execution are disabled for this eval, so the following is the exact required action sequence, not a claim that commands were run.

## Required sequence

1. Resolve the PR and capture its metadata, base/head refs, body, linked issue, existing inline/review/conversation comments, GraphQL review-thread states, and clean working-tree status.
2. Build the manifest from the exact committed diff using:
   ```bash
   git fetch origin <base>
   git rev-list --left-right --count origin/<base>...HEAD
   ```
   Record `B` as the freshly fetched `origin/<base>` SHA and `H0` as the clean committed `HEAD` SHA. Write the exact `B...H0` paths and diff to temporary files, run:
   ```bash
   node /Users/sagar/code/factory/sagar-plugins/plugins/review/skills/review-pr/select-review-lenses.mjs \
     --paths-file <changed-paths> --diff-file <unified-diff>
   ```
   Load the mandatory policy section plus every returned lens section. Include every program-created untracked path, if any, in reviewer scope and accounting.

3. If the first `rev-list` count shows the branch is behind, synchronize only through the authorized rebase procedure:
   ```bash
   git pull origin <base> --rebase
   ```
   Resolve conflicts safely, rerun the full local validation gate, commit only any real synchronization result, fetch the base again, and require zero behind before redefining `B` and `H0`. Do not create an empty commit. If zero behind initially, retain the injected clean, verified, committed `H0`.

4. Because this is broad and high-consequence in a mutating mode, do **not** run a preliminary deep-review pair. Run the mandatory pre-push pair once, in parallel, against the exact committed `B...H0` diff:
   - Fresh primary `change-review`, full selected-lens review.
   - Fresh challenge `change-review`, independent ownership, transition, rule-interaction, completeness, tests, metadata, and CI-parity review.
   - Fresh `security` reviewer in parallel if the selector chose any security-owned lens.

   Each reviewer receives the complete changed-file list, full diff scope, and untracked-file accounting. The supplied pair outcome is acceptable only because both returned native `Assessment` and complete native `Coverage`.

5. Reconcile the pair into one canonical in-scope finding, apply it, run targeted validation plus one fresh integration gate, and commit the real change as `H1`. Do not amend or create an empty commit.

6. Run delta pass 1 with one fresh `change-review` over `H0...H1`, with full `B...H1` context. Add `security` if the correction touched a risk-selected path. It must confirm the pair finding closed and review the correction blast radius. Reconcile its distinct actionable in-scope finding, fix it, validate, and commit `H2`.

7. Run delta pass 2 over `H1...H2`, with full `B...H2` context. Reconcile its distinct actionable in-scope finding, fix it, validate, and commit `H3`.

8. Run delta pass 3 over `H2...H3`, with full `B...H3` context. It reports another distinct actionable in-scope finding.

## Required stop point

The third delta pass consumes the maximum of three allowed delta passes. Therefore, after the third new finding:

- Do **not** edit the third-delta finding.
- Do **not** run targeted validation for a fourth correction.
- Do **not** create a fourth commit.
- Do **not** run a fourth delta review, a replacement pair, or any additional reviewer.
- Do **not** push, update the PR body, watch CI, resolve threads, approve, or merge.

The contract requires a block before any further edit or review call, with the remaining finding reported and a statement that a new user instruction resets the loop budget.

## Delta semantic-acceptance requirement

The prompt explicitly supplies complete native `Assessment` and `Coverage` for the pair, but not for the delta reviewers. Each delta result is usable only if it also contains native `Assessment` and complete native `Coverage`. If a delta result lacks either, retry that reviewer exactly once naming the missing field. If the retry remains incomplete, block immediately instead of accepting the finding or continuing the loop.

# Review

**Mode:** ship  
**Target:** `B...H3`  
**Tier:** deep, the change is broad and high-consequence; the pre-push primary/challenge pair is the required mutating-review mechanism.  
**Assessment:** blocked

### Selected lenses

- `mandatory`, required for every changed behavior.
- Every additional lens returned by `select-review-lenses.mjs`, with its recorded selector signal.
- `security` is required whenever a selected lens is security-owned.

### Findings

- Pair finding: fixed and committed in `H1`.
- Delta 1 finding: fixed and committed in `H2`.
- Delta 2 finding: fixed and committed in `H3`.
- Delta 3 finding: actionable, in-scope, and **remaining**. Its actual `path:line`, mechanism, impact, correction, priority, and confidence must be copied from the accepted reviewer return rather than invented.

### Coverage

- Files read: exact paths from the recorded `B...H0`, `B...H1`, `B...H2`, and `B...H3` manifests.
- Behavior traced: selected lenses, substantial changed codepaths, reviewer challenge concerns, and each correction's blast radius.
- Program units: covered, subject to the approved-program ledger captured from repository evidence.
- Lens evidence: complete only if every reviewer return contains all required selected-lens rows and native Coverage.
- Governing metadata: repository `AGENTS.md`, README, manifests, registries, CI workflows, and PR metadata must be read for changed directories.
- CI-parity matrix: locally runnable required checks must pass, remote-only checks must state their reason.
- Validators: injected local verification passed for `H0`; each of `H1`, `H2`, and `H3` requires fresh targeted validation plus one fresh integration gate.
- Existing comments: must be fetched and triaged before shipping, but cannot be finalized because the loop blocks before push.
- Reviewer returns: pair complete by injected fact; each accepted delta must independently satisfy native `Assessment` and complete native `Coverage`.
- CI at head SHA: not reached, no push is authorized.
- PR body at head SHA: not reached, no push or body update is authorized.

### Approval gate

- Not applicable, the request did not grant explicit approval authority.
- Result: blocked, delta-pass budget exhausted with an actionable in-scope finding remaining. A new user instruction is required to reset the budget.

### Deviations

None.
