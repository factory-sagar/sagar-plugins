# Golden Task 24: Quick Analysis Repo Triage

Version: 1

## Target

`quick-analysis`.

## Setup

```bash
mkdir -p src tests
cat > package.json <<'EOF'
{
  "name": "notes-api",
  "private": true,
  "type": "module",
  "scripts": {
    "start": "node src/index.js"
  },
  "dependencies": {
    "express": "^4.19.0"
  }
}
EOF
cat > src/index.js <<'EOF'
import express from 'express';
import { registerNoteRoutes } from './notes.js';

const app = express();
app.use(express.json());
registerNoteRoutes(app);
app.listen(3000);
EOF
cat > src/notes.js <<'EOF'
export function registerNoteRoutes(app) {
  app.get('/notes', (req, res) => res.json([]));
}
EOF
cat > tests/notes.test.js <<'EOF'
// TODO: no test runner is configured for this repo yet.
EOF
cat > yarn.lock <<'EOF'
# yarn lockfile v1
EOF
cat > package-lock.json <<'EOF'
{ "name": "notes-api", "lockfileVersion": 3, "packages": {} }
EOF
git add -A
git -c user.email=eval@local -c user.name=eval commit -qm "base: express notes api with anomalies"
git branch -m main
```

## Prompt

```text
Triage this repository: stack, structure, entry points, anomalies, and which specialist
should look next. Fast pass only.
```

## Expected behavior

A fast, read-only triage: Node/Express ESM app with `src/index.js` as the entry point, the
two seeded anomalies flagged (competing `yarn.lock` and `package-lock.json`; a `tests/`
directory with no test runner or test script), and a concrete next-droid recommendation.

## Must pass

- Identifies the stack from evidence: Node ESM (`"type": "module"`), Express dependency,
  `npm start` entry via `src/index.js`.
- Flags both seeded anomalies: dual lockfiles, and a tests directory with no configured
  runner or `test` script.
- Recommends a concrete next step or specialist for the anomalies rather than deep-diving
  itself.
- Stays read-only and fast: no file edits, no dependency installation, no server start.

## Must not do

- Edit files, run `npm install`/`yarn`, or start the app.
- Produce an exhaustive file-by-file review instead of a triage.
- Miss both seeded anomalies.
- Recommend nothing.

## Score

- `pass`: stack, entry point, both anomalies, and a next-step recommendation, all
  evidence-based and read-only.
- `partial`: triage is correct but only one seeded anomaly is flagged.
- `fail`: installs or edits anything, misses both anomalies, or turns into a deep review.
