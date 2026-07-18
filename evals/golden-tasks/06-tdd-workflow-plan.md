# Golden Task 06: TDD Workflow Execution

## Target

`tdd-workflow`.

## Setup

```bash
mkdir -p src
cat > package.json <<'EOF'
{
  "type": "module",
  "scripts": {
    "test": "node --test"
  }
}
EOF
cat > src/command-palette.mjs <<'EOF'
export function suggestCommands() {
  throw new Error("not implemented");
}
EOF
cat > src/command-palette.test.mjs <<'EOF'
import test from "node:test";
import assert from "node:assert/strict";

import { suggestCommands } from "./command-palette.mjs";

test("returns no suggestions for an empty command list", () => {
  assert.deepEqual(suggestCommands([], "open"), []);
});
EOF
```

## Prompt

```text
Implement search suggestions for the command palette using TDD. Suggestions should rank prefix
matches above substring matches, hide disabled commands, and preserve the original command order
for equal scores. In the final response, report the behavior statement, standards loaded, each
RED/GREEN slice, and the exact validation evidence.
```

## Expected behavior

The agent should execute vertical Red-Green-Refactor slices around observable behavior. The
repository artifacts must prove RED before GREEN and tests must cover the three requested
behaviors through the exported function.

## Must pass

- Starts from a user-facing or contract-facing behavior statement.
- Loads or references testing, module-design, and type-contract standards; async standards are
  required only if the implementation introduces async behavior.
- Commits or otherwise records failing RED tests before the implementation that makes them pass.
- Uses a vertical slice for the cohesive suggestion behavior; if split into multiple slices,
  each slice goes RED then GREEN before the next starts.
- Includes tests for prefix-vs-substring ranking, disabled command hiding, and stable ordering for equal scores.
- Keeps RED test changes separate from GREEN implementation changes.
- Runs the repository's targeted test command after GREEN and reports the result.

## Must not do

- Implement before writing failing tests.
- Modify tests during GREEN unless the RED tests are invalid.
- Use implementation-detail assertions instead of observable command-palette results.
- Treat coverage percentage as a substitute for the required behavior tests and RED/GREEN
  repository evidence.

## Score

- `pass`: repository evidence proves a standards-aware, behavior-complete RED-to-GREEN execution.
- `partial`: behavior is correct and RED precedes GREEN, but one reporting or separation detail is
  missing.
- `fail`: implementation precedes RED evidence or the run omits a seeded behavior.
