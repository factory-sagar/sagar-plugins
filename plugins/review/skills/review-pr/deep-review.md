# Deep Review Procedure

Internal reference for `review-pr`. Load it only when a change is broad, high-consequence,
or explicitly requests exhaustive review. Authority still comes from `review-pr`; this
procedure never upgrades a report-only request into an editing or remote-write workflow.

Review every change **read-only** first. Match depth to evidence: a light single-pass review
for routine changes, an exhaustive multi-pass review for broad or high-consequence ones.
Only fix, commit, push, approve, or merge when the selected `review-pr` authority mode
explicitly allows that action.

Two phases with a hard wall between them:

1. **Review (read-only).** Reviewer subagents never edit code. They produce findings only.
2. **Fix.** After findings are final, a separate fix phase applies them, verifies, and commits.

Authority comes from `review-pr`: fix mode stops at a local commit; comments, ship, and land
modes continue only as already authorized by the user's original request.

## Inputs

- **Review target** (required): a PR URL/number, a branch name, a commit range (`base..head`),
  or staged/working-tree changes.
- **Depth** (optional): `auto` (default), `light`, or `deep`. `auto` chooses from diff
  evidence and proceeds without making the user select the method.
- **Specific concerns** (optional): if the user has particular questions, prioritize them.

## Supporting files

This skill ships three supporting files alongside this one. The manager (you) must Read the
ones a run needs in full, and pass their **absolute installed paths** into subagent prompts:

- `review-notes-format.md` — the shared notes-doc skeleton, pattern-check / codepath / finding
  formats, and filter annotations. Used by the deep tier.
- `review-worker.md` — exact prompt templates for the deep-tier Review subagent (initial context
  load, model-driven pass, convention pass, final filter) plus its anti-patterns and
  challenge-response rules. Substitute placeholders; do not rewrite the prompt bodies.
- `discover-conventions.md` — the procedure the deep-tier Discovery subagent follows to
  enumerate applicable conventions into the notes doc.

When a prompt below says `<FORMAT_DOC>`, `<WORKER_DOC>`, or `<DISCOVERY_DOC>`, substitute the
real absolute path of that supporting file as installed on disk. When it says `<NOTES_PATH>`,
substitute the notes-doc path you created in Step 3b.

## Two tiers

| Tier | When | Review shape | Cost |
| --- | --- | --- | --- |
| **Light** (default) | Routine PRs, small/medium diffs, no risk signals | One read-only pass via the `change-review` droid (plus `security` if risk signals) | 1-3 subagent calls |
| **Deep** (opt-in / auto-escalated) | Large or risky PRs | Convention discovery + resumed multi-pass review over a shared notes doc; exhaustive "finding or verified-clean" per item | Many subagent calls, slow |

Both tiers share the same tail: consolidate findings → fix → verify → commit (no push) → summary.

## Workflow

### 1. Resolve the scope and load the diff

Determine the base ref and collect the diff plus file/line stats. Use whichever applies:

```bash
# PR
gh pr view <url> --json number,title,author,headRefName,baseRefName,state,body
gh pr diff <url>
# PR — existing review threads (MANDATORY whenever the target is a PR)
gh api repos/<owner>/<repo>/pulls/<number>/comments   # inline review comments
gh pr view <url> --json reviews,comments              # review summaries + PR-level comments

# branch vs base
git diff --stat <base>...<branch>
git diff <base>...<branch>

# staged / working tree
git diff --stat --staged
git diff --staged
```

Capture: changed file count, total added+removed lines, and the list of changed paths. You
need these for the tier heuristic in Step 2.

**Existing review comments are inputs to this review, not someone else's problem.** When the
target is a PR, carry every unresolved actionable comment (bot or human) into the Step 4
findings list with source `pr-thread` and triage it like any other finding — fix it, or reject
it with a written reason. A review-pr pass on a PR that ends with untriaged existing threads
is incomplete, no matter what else it fixed.

**Rolling / stacked PRs:** if commit subjects or the PR body describe per-unit landing, do
not review the whole branch as one blob. Use the unit named by the request; otherwise scope
to commits not yet reviewed. Apply the tier heuristic to each unit rather than the branch
total.

Every mode stays in the current repository checkout. Report mode performs no branch mutation.
In mutating modes, follow the disposable-checkout policy in `fix-comments.md`, then check out
the PR branch natively. Only a checkout explicitly marked with
`workflow.disposableCheckout=true` may discard local state; an unmarked dirty checkout blocks
the workflow. Never create a secondary checkout or clone.

### 2. Choose the tier (auto-heuristic)

Use the canonical classification in `review-pr/SKILL.md`: deep review is mandatory above its
file/unit/lens thresholds and for the high-consequence responsibilities it names. An explicit
`deep` request upgrades review; an explicit `light` request cannot bypass a mandatory deep
condition. Otherwise use light review. State the evidence and proceed without asking the user
to select the method.

---

### 3a. Review — Light tier

Spawn the `change-review` droid once on the scope. If any risk-sensitive path is in the diff,
spawn `security` in parallel (same message, two `Task` calls).

```
Task(subagent_type: "change-review", description: "Review change scope",
  prompt: "Review <scope: PR URL / base..head / staged>. Return your standard label-list
  output (Summary, Assessment, What This Change Does, Coverage, Findings, Validation Notes).
  Every finding carries a [P<n>·<conf>] label and a path:line anchor. Read-only; do not edit.")

# only if risk signals present:
Task(subagent_type: "security", description: "Security review change scope",
  prompt: "Security-review <scope> through STRIDE/OWASP lenses. Return findings with severity,
  confidence, attack path, and path:line anchors. Read-only; do not edit.")
```

Collect findings from both. These droids are read-only by contract; do not let them edit.
Proceed to Step 4.

---

### 3b. Review — Deep tier (manager-only orchestration)

The deep tier is an **orchestration**: you (the manager) coordinate two subagents over a shared
notes doc and never read the PR or load convention docs yourself. Read `<FORMAT_DOC>`,
`<WORKER_DOC>`, and `<DISCOVERY_DOC>` in full before spawning anything.

#### Subagents

All deep-tier subagents run as `review-worker` (pinned to the reviewing model), NOT the
generic `worker` — `worker` inherits the session model, so a cheap session would silently
degrade every deep pass. If `review-worker` is unavailable (plugin not installed), fall back
to `worker` and say so in the report.

- **`Discovery` subagent** (Step 3b-i only): a single `review-worker` `Task` call that follows
  `<DISCOVERY_DOC>` to crawl convention sources and append every applicable pattern-check to the
  notes doc. It returns a two-field summary (final pattern-check count + source docs); the real
  output lives in the notes doc.
- **`Review` subagent** (Step 3b-ii to initialize, then RESUMED for every pass and the final
  filter): a single `review-worker` `Task` call to initialize, followed by `Task` calls with
  `resume: <task_id>` for every subsequent pass. It accumulates context (PR intent, prior
  findings, convention docs it has read) across passes. **Never spawn a fresh Review per pass**
  — always resume the same one. Both subagents are **read-only on the repo** and may write only
  to the notes doc.

Capture the `task_id` from the initial Review call and reuse it as `resume` everywhere after.
Each resume adds ONLY what is new for that pass; do not re-send context it already has.

#### Resume reliability — verify the notes doc, and fall back if resume is not writing

The resumed-session pattern is leaky in two observed ways. Guard against both:

1. **The reply body is not the deliverable.** A resume often echoes the PREVIOUS pass's summary
   text in its reply even though the new pass wrote correctly to the notes doc. Trust the notes
   doc, not the reply. After each pass do ONE targeted check: read the notes-doc sections the pass
   should have appended to and confirm NEW entries exist. Do not re-read or re-grep the reply body
   to "confirm" work landed — that burns calls for nothing.

2. **Resume can silently no-op.** In some environments a resume returns the prior turn's cached
   output and writes NOTHING new to the notes doc. Detect this via the audit in Step 3b-iii.4: if a
   pass added zero new codepath notes / verdicts / findings, the resume did not actually execute —
   do NOT trust its `completed`-looking summary.

   **Sanctioned fallback (comprehensive worker):** when resume is verified not to be writing to
   the notes doc, stop resuming. Spawn ONE fresh `review-worker` that loads the diff once and, in a single
   session, walks ALL pattern-checks already enumerated in the notes doc by Discovery PLUS the
   mandatory model-driven concerns (Functional Correctness; Ownership, Transition, and Rule
   Interaction; Impact; Completeness), appending every
   codepath note and finding to the notes doc in the normal format. This preserves the deep tier's
   thoroughness and is far more reliable than many broken resume round-trips. For very large diffs
   (20+ categories), prefer this fallback proactively — the per-category round-trip model is
   expensive and brittle, and one comprehensive worker reading Discovery's output is a better fit.

#### Step 3b-i — Create the notes doc and launch Discovery + initial Review (in parallel)

Using `<FORMAT_DOC>`, create the notes doc at a stable path outside the repo and capture
`<NOTES_PATH>`. Then launch the Discovery `Task` and the initial Review `Task` **in the same
message** so they load the diff concurrently.

Discovery prompt:
```text
Use the convention-discovery procedure in <DISCOVERY_DOC>. Run it against the diff from
<scope> vs base ref <base>.

Notes doc path: <NOTES_PATH>
Review notes format: <FORMAT_DOC>
Convention backstop (if installed): ../../../practices/skills/coding-standards/SKILL.md and its
topic docs; if that relative path does not resolve, Glob for
"**/practices/skills/coding-standards/SKILL.md" before treating the backstop as absent. Also
discover the TARGET repo's own convention docs (Glob "docs/**/*.md",
"**/AGENTS.md", touched-workspace READMEs).

Append every pattern-check you produce to the "## Pattern Checks" section of the notes doc using
the entry format in the review notes format. In your final step, DELETE any pattern-check you can
justify as definitely inapplicable. Do NOT return the pattern-checks as JSON — the notes doc is
the deliverable. Your final response is a short summary: the count of pattern-check entries left
and the unique source docs cited. Read-only on the repo; only the notes doc is writable.
```

**Discovery has a hard 5-minute budget.** Capture its `task_id` and poll with
`TaskOutput(task_id, block: false)` while you wait. If it is still running 5 minutes after
launch, call `TaskStop(task_id)` and proceed with whatever it wrote (possibly zero — the
mandatory passes still run with default docs). Do not spawn a "finish discovery" follow-up.

Initial Review prompt: use the `Initial Review prompt` section of `<WORKER_DOC>`, substituting
`<scope>`, `<NOTES_PATH>`, and `<FORMAT_DOC>`. Capture its `task_id`.

Wait for both to return (or for Discovery's timeout-stop) before proceeding. Then `Read` the
`## Pattern Checks` section of the notes doc; the doc, not the reply, is canonical.

#### Step 3b-ii — Define the review plan

Group the pattern-checks by `category`. Each unique category becomes one pass. Use `TodoWrite`
to create one TODO per pass, in this order, then a Final reconciliation TODO:

- **Functional Correctness** (mandatory, model-driven — does not consume pattern-checks)
- **Ownership, Transition, and Rule Interaction** (mandatory, model-driven)
- **User and System Impact** (mandatory, model-driven)
- **Completeness** (mandatory, model-driven)
- **Code Organization** (mandatory — runs all `Code Organization` pattern-checks)
- **Style guide** (mandatory — runs all `Style guide` pattern-checks)
- One pass per other unique `category` present (e.g. `Backward Compatibility`, `Error & Logging`)
- A dedicated **Security** pass via the `security` droid when risk-sensitive paths are present
- **Final reconciliation**

The first six passes are mandatory and run even if Discovery emitted zero pattern-checks for
them. Never start with style or cosmetic observations.

#### Step 3b-iii — Execute passes one at a time (strict state machine)

For each pass, in order:

1. **Mark `in_progress`** (only this pass; later passes stay `pending`).
2. **Prepare the Pass Expectations** for the Review subagent:
   - **Passes 1-4 (model-driven)** do NOT consume pattern-checks. For each new/changed codepath
     in scope, the Review must emit at least one finding OR a detailed verified-clean explanation
     (Pass 1: reachable + validated + error/state contract handled; Pass 2: every state writer,
     terminal event, retained dependency, and simultaneously applicable rule has been traced and
     the intended winner proven; Pass 3: user/ops impact is acceptable and observable; Pass 4:
     fully wired, tested, documented, and represented in repository metadata and CI).
   - **Passes 5+ (pattern-check-driven)**: every pattern-check in the pass's category must get a
     finding OR a detailed explanation of why it does not apply.
3. **Execute the pass** with a `Task` call `resume: <Review task_id>` using the matching template
   from `<WORKER_DOC>` (`Model-driven pass prompt` for 1-4, `Convention pass prompt` for 5+).
   For convention passes, filter the pattern-checks to the pass's category and compute the unique
   `source_doc` set; the prompt tells the Review to Read those docs first (if not already read).
   When the filtered list is empty, instruct it to Read the matching default doc and walk every
   H3 subsection. For the Security pass, instead spawn the `security` droid on the scope and fold
   its findings into the notes doc.
4. **Audit the notes doc.** Confirm coverage: model-driven passes have a `## Codepath Notes`
   entry per substantial changed codepath; convention passes have a verdict for every in-scope
   pattern-check; every `finding` verdict has a `## Findings` block. If anything is `pending`,
   send a targeted resume naming the specific items before moving on.
5. **Mark `completed`** only after the pass summary is emitted AND the audit passes.

**Hard rules (violations invalidate the review):**
- Do not emit final output until every TodoWrite item is `completed` with a `--- Pass N complete ---`
  summary in your response.
- Do not batch-mark multiple passes `completed`; one update per pass, after its summary.
- Do not mark a pass `completed` to satisfy a system reminder. If reminders reveal pending TODOs,
  go execute them.
- Do not spawn a fresh Review per pass **while resume is working**. The one exception is the
  sanctioned comprehensive-worker fallback when resume is verified not to be writing to the notes
  doc (see "Resume reliability" above).
- A legitimately empty pass still needs a summary ("Considered: none — <why>").

#### Step 3b-iv — Final reconciliation

1. **Manager pre-flight (no subagent call):** every pass `completed`; every pattern-check has a
   verdict (not `pending`); `verified-clean` verdicts cite concrete `file:line`, not generic
   compliance language; count distinct finding blocks (call it `N`).
2. **Review final filter:** one `Task` call `resume: <Review task_id>` using the `Final filter
   prompt` in `<WORKER_DOC>`. It marks invalid findings filtered using the closed-list reasons;
   it does not rewrite finding bodies.
3. **Manager reads the notes doc**, takes every unfiltered finding into Step 4.

#### Step 3b-v — Independent challenge review

Spawn one fresh `review-worker` that has not seen the primary notes or findings. Give it the
full scope, intent, selected lenses, governing repository metadata, and these model-driven
concerns:

- functional correctness;
- ownership, transition, and rule interaction;
- completeness, test seams, metadata, and CI parity.

Require one finding or verified-clean `path:line` entry for every changed file and substantial
codepath. Store its output separately from the primary notes. The manager then reconciles the
union of primary and challenge findings in Step 4. The primary comprehensive-worker fallback
does not replace this independent pass.

---

### 4. Consolidate findings into an actionable list

Merge findings from whichever tier ran. De-duplicate. Triage each (do not blindly apply):

| Classification | Action |
| --- | --- |
| **Real bug** | Fix it. |
| **Valid improvement** | Fix it. |
| **Style nit** | Fix only if it matches repo conventions; otherwise note and skip. |
| **False positive** | Skip. Note a one-line reason in the summary. |
| **Out of scope** | Skip. Note as context; do not widen the change. |

The reviewers are read-only; fixes happen in Step 5, not during review.

**Verify before classifying.** Check each finding against the ACTUAL diff and its tests before
calling it a bug. Behavior that looks like a regression is often intentional and test-enforced
(e.g. a status code newly asserted by added route tests, or intra-file clone records a
duplicate-checker deliberately relies on). If the tests assert the "new" behavior, it is not a
bug — mark it a false positive. Blindly applying these would break tests and CI.

**Product decisions are not bugs.** A finding that challenges a product/design choice (a widened
capability, a visibility flag) is a decision for the operator, not an auto-fix. Check peer
implementations and intent (comments, ticket) first; if it is a genuine product choice, surface it
and do not revert it.

**When a finding admits two valid fixes** (e.g. "render or remove the unused field"), default to
the lowest-risk option (YAGNI: remove the unused path) rather than adding unrequested product
surface. If the choice is genuinely a product-direction call, surface it instead of deciding it.

### 5. Fix the actionable findings

Run this step only in `fix`, `comments`, `ship`, or `land` mode. In `report` mode, return
the reconciled findings without editing.

For each **real bug** / **valid improvement** (and accepted nits):

- Read the file and surrounding code before editing.
- Group fixes by file; apply all changes to a file before moving on (avoids line drift). If a
  finding cites a line you already edited, relocate by content, not line number.
- Re-read each file after editing to confirm the fix is correct.
- **Deviations contract**: when the code contradicts a finding's suggested fix but the finding
  is real, take the conservative fix and log the deviation (plan / territory evidence / chose /
  impact) for the summary. If the contradiction invalidates the finding's premise, reclassify
  it as a false positive instead of forcing the fix. Never deviate silently.

If the `build` plugin is installed and the fix set is substantial, you may delegate to the
`implementer` droid with the consolidated finding list. Otherwise apply the edits inline.

### 6. Verify

Discover the project's checks (read `package.json`, `Makefile`, `pyproject.toml`, or
`.github/workflows/`). Typical: format, lint, typecheck, tests — plus any repo-specific validators
the diff implicates (e.g. knip for unused exports, a duplicate-code checker, an `AGENTS.md` /
frontmatter validator when you edited those files). Run validators for the file types you actually
touched.

Run in an efficient order: the **affected/changed-area tests first** (fast feedback on your
fixes), then the **full suite** and the repo-specific validators. If the repo declares a master
gate (`npm run verify`, `make check`, a CI-mirroring script), finish with that — it is the
definition of green, not your reconstruction of it.

```bash
npm run format && npm run lint && npm run typecheck
npm test -- <changed area>     # affected tests first
npm test                       # then the full suite
npm run verify                 # master gate last, when the repo declares one
```

**Ratchet / freeze gates:** repos may enforce shrink-only baselines (inline-5xx counts, `.sort`
counts, size budgets, dependency-age gates). If one of your fixes trips such a gate, make the
code comply — never raise a baseline to get green. If a fix legitimately lowers a count, lower
the baseline in the same commit to lock in the win.

Fix any failure your changes introduced before committing. Do not commit broken code.

### 7. Commit — do NOT push

Run this step only in a mutating mode. `report` mode never stages or commits.

Stage and commit with a conventional-commit message summarizing the fixes. **Do not push.**

```bash
git add -A
git commit -m "fix: address review findings on <scope>

- <one bullet per fix: file + what changed>

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>"
```

Use a heredoc (`git commit -F -`) if the message contains special characters.

### 8. Summarize and return to the authority mode

Report:
- Tier used (light / deep) and why.
- Findings: <N> total, <M> fixed, <K> skipped (one-line reason each).
- Review threads (PR targets): <T> existing, <F> fixed+resolved, <R> rejected with reply,
  <U> unresolved (list them). Omit only for non-PR targets.
- Fixed: one line per fix (file + change).
- Deviations: any fix applied differently than the finding suggested (or `none`).
- Verification: format/lint/typecheck/test status.
- Commit SHA created (not pushed).

In fix mode, stop here. In comments, ship, or land mode, continue because the original user
request already authorized the stronger remote workflow. Never ask the user to repeat
authority they already provided.

### 9. Close the loop on a PR

Run this step only in `comments`, `ship`, or `land` mode. Approval and merge require
explicit approval or merge intent; comment handling alone does not grant either authority.

This skill's core scope ends at push. What happens next depends on what the user asked for
in the invocation:

**User did not ask to land it:** after a confirmed push, offer the handoff — comment /
resolve threads / approve / merge → `review-pr` comments mode (or `ship`) on the same PR.

**User explicitly asked to land it ("merge when green", "keep it ready and merge", etc.):**
landing has a hard gate. Verify ALL of the following against the live API, in order, before
any approve or merge:

1. Every `pr-thread` finding from Step 1 is closed: fixed items have a reply on their thread
   and the thread resolved; rejected items have a reply with the reasoning. Re-fetch the
   thread list now — new comments may have arrived since Step 1.
2. Zero unresolved review threads remain (`gh api repos/<o>/<r>/pulls/<n>/comments` +
   review threads). An unresolved thread is a hard merge blocker, even with green CI and an
   explicit merge instruction — stop and report the remaining threads instead of merging.
3. CI is green (`gh pr checks`).
4. The PR body still describes the PR after your fixes; regenerate it if the scope moved.

Only when all four hold: approve (if not your own PR) and merge. If any check fails, report
what is outstanding and stop. Never auto-merge without an explicit user instruction from this
session.

## Severity discipline

- **Blocking**: must be fixed before merge (data loss, auth bypass, crash on common path, secret leak).
- **Non-blocking**: works but should improve; convention-anchored findings are usually here.
- **Nit**: take it or leave it.

A non-blocking finding with a documented convention citation is more valid than a blocking
finding without evidence. Do not drop convention findings for being "minor"; that is exactly the
bias the filter's closed-list reasons exist to prevent.

## What Not to Do

- Do not let reviewer subagents edit code. Review is read-only; fixes are a separate phase.
- In `report` and `fix` modes, do not push. Stronger modes continue only because the
  original request already granted remote-write authority.
- Do not approve or merge while any review thread is unresolved. Untriaged existing comments
  are a hard blocker even when the user said "merge when green"; burying reviewer comments
  under a merge is a hard failure of this workflow.
- Do not skip fetching existing PR threads in Step 1. Absence of knowledge about threads is
  not absence of threads.
- Do not run the deep tier on a small routine diff. Default light; escalate only on the heuristic.
- Do not escalate to deep on a small, well-tested touch to a risk-sensitive path alone. Escalate
  only when the diff is also large or the risk-sensitive logic is new/rewritten.
- Do not ask the user to select light versus deep; select from evidence and report why.
- Do not trust a resume's `completed`-looking summary or reply body. Confirm new entries actually
  landed in the notes doc; if a resume wrote nothing, switch to the comprehensive-worker fallback.
- Do not auto-fix a finding that challenges a product/design decision; surface it to the operator.
- Do not treat test-enforced behavior as a regression. Verify findings against the tests first.
- Do not lead the review with style/naming. Functional correctness comes first.
- Do not widen scope: fix the reviewed change, not pre-existing issues outside it.
- Do not blindly apply suggestions; triage each one and skip false positives with a reason.
- Do not, in the deep tier, read the PR or convention docs as the manager. Delegate to subagents.
- Do not spawn a fresh deep-tier Review subagent per pass; resume the same one.
- Do not commit if format/lint/typecheck/test fails for reasons your changes caused.
