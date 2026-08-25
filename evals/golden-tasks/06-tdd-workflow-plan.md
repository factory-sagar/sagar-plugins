# Golden Task 06: TDD Workflow Execution

Version: 2

## Target

`tdd-workflow`.

## Intent

The run exists to implement command-palette suggestions through a standards-aware, observable
RED-to-GREEN workflow that proves ranking, disabled-command filtering, and stable ordering.
Success means repository evidence shows each behavior-bearing slice failing before it passes; a
correct implementation with RED preceding GREEN but one reporting or separation detail missing
remains partial achievement, while implementation before RED evidence or omission of a seeded
behavior misses the point.

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

## Fulfillment

- Starts from a user-facing or contract-facing behavior statement.
- Loads or references testing, module-design, and type-contract standards; async standards are
  required only if the implementation introduces async behavior.
- Commits or otherwise records failing RED tests before the implementation that makes them pass.
- Uses a vertical slice for the cohesive suggestion behavior; if split into multiple slices,
  each slice goes RED then GREEN before the next starts.
- Includes tests for prefix-vs-substring ranking, disabled command hiding, and stable ordering for equal scores.
- Keeps RED test changes separate from GREEN implementation changes.
- Runs the repository's targeted test command after GREEN and reports the result.

## Boundaries

- Implement before writing failing tests.
- Modify tests during GREEN unless the RED tests are invalid.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
