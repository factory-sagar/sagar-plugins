# Golden Task 21: PR Description Is Self-Contained and Diff-Grounded

Version: 2

## Target

`pr-describer`.

## Intent

Provide a self-contained, diff-grounded PR title and structured body explaining the bounded
poll, its rationale, truthful unexecuted-test status, and breaking-change impact for a reviewer
without session knowledge; leaked session or tooling context, invented artifacts, fabricated
test results, or unsupported behavior descriptions miss this goal.

## Setup

```bash
mkdir -p src
cat > src/poll.js <<'EOF'
export async function pollUntilReady(check) {
  while (true) {
    if (await check()) return true;
  }
}
EOF
git add -A
git -c user.email=eval@local -c user.name=eval commit -qm "chore: base poller"
git branch -m main
git checkout -qb feature/poll-bound
cat > src/poll.js <<'EOF'
const MAX_POLLS = 120;

export async function pollUntilReady(check) {
  for (let attempt = 0; attempt < MAX_POLLS; attempt += 1) {
    if (await check()) return true;
  }
  return false;
}
EOF
cat > src/poll.test.js <<'EOF'
import { pollUntilReady } from './poll.js';

test('gives up after the poll bound instead of spinning forever', async () => {
  expect(await pollUntilReady(async () => false)).toBe(false);
});
EOF
git add -A
git -c user.email=eval@local -c user.name=eval commit -qm "fix(poll): bound the ready poll loop"
```

## Prompt

```text
Write the PR title and body for branch feature/poll-bound against main. GitHub is
unavailable in this environment, so do not run gh; produce the description from the local
diff. The description must stand alone for a reviewer who knows nothing about this session.
```

## Fulfillment

- Uses an imperative title describing the poll-bounding change.
- Explains the `MAX_POLLS` bound, `false` on exhaustion, and the previous unbounded loop in
  a body grounded in the actual diff.
- Includes a truthful testing section that names the added test and says it was not executed
  here (or asks CI to run it).
- Accurately explains that callers now receive `false` on timeout instead of hanging, or
  explicitly says there is no breaking change with reasoning.
- Supplies a self-contained description that a reviewer can understand without session knowledge.

## Boundaries

- Reference the session, the eval, the agent, prompts, or internal tooling in the output.
- Invent issue numbers, reviewers, links, or CI results.
- Claim the test suite ran or passed.
- Describe files or behavior not present in the diff.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
