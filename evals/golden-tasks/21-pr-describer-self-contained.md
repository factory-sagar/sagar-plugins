# Golden Task 21: PR Description Is Self-Contained and Diff-Grounded

Version: 1

## Target

`pr-describer`.

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

## Expected behavior

A PR title and structured body (what, why, testing, breaking changes) that describes the
bounded-poll change itself, grounded in the diff, honest that the test was not executed
here, with no session, process, or tooling references.

## Must pass

- Title describes the poll-bounding change in the imperative, not the work session.
- Body explains what changed (`MAX_POLLS` bound, `false` on exhaustion) and why (the
  previous loop could spin forever), grounded in the actual diff.
- Testing section is truthful: names the added test and states it was not executed in this
  environment (or asks that CI run it), rather than claiming a green run.
- States breaking-change impact accurately (callers now receive `false` on timeout instead
  of hanging), or explicitly says none with reasoning.
- Reads as self-contained: a reviewer needs no knowledge of this eval, session, or tools.

## Must not do

- Reference the session, the eval, the agent, prompts, or internal tooling in the output.
- Invent issue numbers, reviewers, links, or CI results.
- Claim the test suite ran or passed.
- Describe files or behavior not present in the diff.

## Score

- `pass`: self-contained, diff-grounded title and body with truthful testing and
  breaking-change sections.
- `partial`: grounded description but one section (testing or breaking changes) is missing
  or vague.
- `fail`: session/process references, invented artifacts, or fabricated test claims.
