---
name: review-fix
version: 1.1.0
description: |
  Review a change end-to-end, then fix it. Runs a read-only review (light by default,
  deep on demand), consolidates findings, applies the fixes in code, verifies, commits
  locally, and STOPS before pushing so you can approve. Picks the tier automatically:
  light single-pass for regular PRs, deep exhaustive multi-pass for large or risky ones,
  confirming before it escalates.
  Use when:
  - The user says "review and fix", "review this PR and fix it", "deep review and fix"
  - The user gives a PR URL / branch / commit range and wants findings fixed, not just reported
  - The user wants exhaustive review for a risky change but a quick one for routine changes
  - The user wants review findings applied and committed locally, then to approve before push
---

# Review and Fix

Take a change, review it **read-only**, fix every actionable finding, verify, and commit
locally **without pushing**. Match the review depth to the change: a light single-pass review
for routine PRs, an exhaustive multi-pass review for large or risky ones.

Two phases with a hard wall between them:

1. **Review (read-only).** Reviewer subagents never edit code. They produce findings only.
2. **Fix.** After findings are final, a separate fix phase applies them, verifies, and commits.

The skill always stops at a local commit and asks before pushing.

## Inputs

- **Review target** (required): a PR URL/number, a branch name, a commit range (`base..head`),
  or staged/working-tree changes.
- **Depth** (optional): `auto` (default), `light`, or `deep`. `auto` chooses per the heuristic
  in Step 2 and confirms via `AskUser` before escalating to deep.
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

# branch vs base
git diff --stat <base>...<branch>
git diff <base>...<branch>

# staged / working tree
git diff --stat --staged
git diff --staged
```

Capture: changed file count, total added+removed lines, and the list of changed paths. You
need these for the tier heuristic in Step 2.

If the target is a PR, check out its branch (see the `fix-pr` skill's checkout step) so you can
apply fixes locally. For a local branch / staged changes, work in place. Confirm the working
tree is clean before editing: `git status --porcelain`.

### 2. Choose the tier (auto-heuristic)

If the user explicitly passed `light` or `deep`, honor it and skip the heuristic.

Otherwise default to **light**, and auto-suggest **deep** when ANY of these hold:

- **Size**: more than ~50 changed files OR more than ~2000 added+removed lines.
- **New/rewritten risk-sensitive logic**: the diff touches authentication / authorization,
  session or consent handling, secrets/credentials, database migrations or schema,
  payments/billing, public API contracts or shared types, or concurrency/locking primitives —
  **AND that sensitive logic is genuinely new or substantially rewritten**, not a small edit to
  existing, well-tested code.
- **User signal**: the user explicitly asked for deep, or described the change as risky.

**A small, well-tested touch to a risk-sensitive path is NOT enough on its own.** In practice
that over-escalates: deep then runs many sequential passes only to return convention nits at high
latency. When a risk-sensitive path is touched but the change is small and the existing code is
already well-built and tested, prefer **light** — `change-review` + `security` in parallel surface
the same findings at a fraction of the cost — and note why. Reserve deep for diffs that are also
large, or where the risk-sensitive logic itself is new or rewritten.

When the heuristic suggests deep, confirm before escalating:

```
AskUser:
1. [question] This change looks large or risky (<one-line reason, e.g. "78 files, touches auth + a DB migration">). Run the deep exhaustive review, or the light review?
[topic] Review Depth
[option] Deep (exhaustive multi-pass)
[option] Light (single pass)
```

If no signal fires, proceed light without asking. State which tier you chose and why in one
sentence before reviewing.

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

- **`Discovery` subagent** (Step 3b-i only): a single `worker` `Task` call that follows
  `<DISCOVERY_DOC>` to crawl convention sources and append every applicable pattern-check to the
  notes doc. It returns a two-field summary (final pattern-check count + source docs); the real
  output lives in the notes doc.
- **`Review` subagent** (Step 3b-ii to initialize, then RESUMED for every pass and the final
  filter): a single `worker` `Task` call to initialize, followed by `Task` calls with
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
   the notes doc, stop resuming. Spawn ONE fresh `worker` that loads the diff once and, in a single
   session, walks ALL pattern-checks already enumerated in the notes doc by Discovery PLUS the
   mandatory model-driven concerns (Functional Correctness, Impact, Completeness), appending every
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
topic docs. Also discover the TARGET repo's own convention docs (Glob "docs/**/*.md",
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
- **User and System Impact** (mandatory, model-driven)
- **Completeness** (mandatory, model-driven)
- **Code Organization** (mandatory — runs all `Code Organization` pattern-checks)
- **Style guide** (mandatory — runs all `Style guide` pattern-checks)
- One pass per other unique `category` present (e.g. `Backward Compatibility`, `Error & Logging`)
- A dedicated **Security** pass via the `security` droid when risk-sensitive paths are present
- **Final reconciliation**

The first five passes are mandatory and run even if Discovery emitted zero pattern-checks for
them. Never start with style or cosmetic observations.

#### Step 3b-iii — Execute passes one at a time (strict state machine)

For each pass, in order:

1. **Mark `in_progress`** (only this pass; later passes stay `pending`).
2. **Prepare the Pass Expectations** for the Review subagent:
   - **Passes 1-3 (model-driven)** do NOT consume pattern-checks. For each new/changed codepath
     in scope, the Review must emit at least one finding OR a detailed verified-clean explanation
     (Pass 1: reachable + validated + error/state contract handled; Pass 2: user/ops impact is
     acceptable and observable; Pass 3: fully wired, tested, documented for what it adds).
   - **Passes 4+ (pattern-check-driven)**: every pattern-check in the pass's category must get a
     finding OR a detailed explanation of why it does not apply.
3. **Execute the pass** with a `Task` call `resume: <Review task_id>` using the matching template
   from `<WORKER_DOC>` (`Model-driven pass prompt` for 1-3, `Convention pass prompt` for 4+).
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

For each **real bug** / **valid improvement** (and accepted nits):

- Read the file and surrounding code before editing.
- Group fixes by file; apply all changes to a file before moving on (avoids line drift). If a
  finding cites a line you already edited, relocate by content, not line number.
- Re-read each file after editing to confirm the fix is correct.

If the `build` plugin is installed and the fix set is substantial, you may delegate to the
`implementer` droid with the consolidated finding list. Otherwise apply the edits inline.

### 6. Verify

Discover the project's checks (read `package.json`, `Makefile`, `pyproject.toml`, or
`.github/workflows/`). Typical: format, lint, typecheck, tests — plus any repo-specific validators
the diff implicates (e.g. knip for unused exports, a duplicate-code checker, an `AGENTS.md` /
frontmatter validator when you edited those files). Run validators for the file types you actually
touched.

Run in an efficient order: the **affected/changed-area tests first** (fast feedback on your
fixes), then the **full suite** and the repo-specific validators.

```bash
npm run format && npm run lint && npm run typecheck
npm test -- <changed area>     # affected tests first
npm test                       # then the full suite
```

Fix any failure your changes introduced before committing. Do not commit broken code.

### 7. Commit — do NOT push

Stage and commit with a conventional-commit message summarizing the fixes. **Do not push.**

```bash
git add -A
git commit -m "fix: address review findings on <scope>

- <one bullet per fix: file + what changed>

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>"
```

Use a heredoc (`git commit -F -`) if the message contains special characters.

### 8. Summarize and ask before pushing

Report:
- Tier used (light / deep) and why.
- Findings: <N> total, <M> fixed, <K> skipped (one-line reason each).
- Fixed: one line per fix (file + change).
- Verification: format/lint/typecheck/test status.
- Commit SHA created (not pushed).

Then ask:

```
AskUser:
1. [question] Fixes are committed locally on <branch> (<sha>), not pushed. Push now?
[topic] Push
[option] Push to remote
[option] Don't push, I'll review first
```

Only push if confirmed:
```bash
git push origin <branch-name>
```

### 9. Close the loop on a PR (optional)

This skill's core scope ends at push. If the target is a PR and the user wants the loop closed
(post a summary comment, reply to and resolve review threads, approve, merge), that is the `fix-pr`
skill's job, not this one. After a confirmed push, offer the handoff:

- Comment / resolve threads / approve / merge → run the `fix-pr` skill (or `gh` CLI) on the same PR.

Do not auto-merge. Merging is an explicit, separate user decision.

## Severity discipline

- **Blocking**: must be fixed before merge (data loss, auth bypass, crash on common path, secret leak).
- **Non-blocking**: works but should improve; convention-anchored findings are usually here.
- **Nit**: take it or leave it.

A non-blocking finding with a documented convention citation is more valid than a blocking
finding without evidence. Do not drop convention findings for being "minor"; that is exactly the
bias the filter's closed-list reasons exist to prevent.

## What Not to Do

- Do not let reviewer subagents edit code. Review is read-only; fixes are a separate phase.
- Do not push. The skill stops at a local commit and asks first.
- Do not run the deep tier on a small routine diff. Default light; escalate only on the heuristic.
- Do not escalate to deep on a small, well-tested touch to a risk-sensitive path alone. Escalate
  only when the diff is also large or the risk-sensitive logic is new/rewritten.
- Do not escalate to deep without confirming via AskUser (unless the user asked for deep).
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
