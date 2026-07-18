# Golden Task 22: Planner Decomposition with Repo Evidence

Version: 1

## Target

`planner`.

## Setup

```bash
mkdir -p src/routes src/store docs
cat > src/routes/notes.js <<'EOF'
import { listNotes, createNote, deleteNote } from '../store/notes.js';

export function registerNoteRoutes(app) {
  app.get('/notes', async (req, res) => res.json(await listNotes(req.user.id)));
  app.post('/notes', async (req, res) => res.json(await createNote(req.user.id, req.body)));
  app.delete('/notes/:id', async (req, res) => {
    await deleteNote(req.user.id, req.params.id);
    res.status(204).end();
  });
}
EOF
cat > src/store/notes.js <<'EOF'
const notes = new Map();

export async function listNotes(userId) {
  return [...notes.values()].filter((note) => note.userId === userId);
}

export async function createNote(userId, data) {
  const note = { id: String(notes.size + 1), userId, ...data };
  notes.set(note.id, note);
  return note;
}

export async function deleteNote(userId, id) {
  const note = notes.get(id);
  if (note && note.userId === userId) notes.delete(id);
}
EOF
cat > docs/conventions.md <<'EOF'
# Conventions
- Route handlers stay thin; behavior lives in src/store modules.
- Destructive endpoints require an ownership check in the store layer.
EOF
git add -A
git -c user.email=eval@local -c user.name=eval commit -qm "base: notes routes and store"
git branch -m main
```

## Prompt

```text
Plan this feature: notes get soft-delete instead of hard delete, plus a restore endpoint
(POST /notes/:id/restore). Deleted notes disappear from listing but restorable ones must
survive. Produce the plan only; do not implement.
```

## Expected behavior

An evidence-anchored plan: a territory scan citing the actual files, the soft-delete
representation decision compared against at least one rejected alternative, agent-sized
units with executors and dependency order, and open questions with recommended answers.

## Must pass

- Territory scan cites real evidence (`src/routes/notes.js`, `src/store/notes.js`,
  `docs/conventions.md`) with the behavior each contributes.
- Makes the soft-delete representation decision explicitly (for example a `deletedAt`
  field versus a separate collection) and records at least one rejected alternative with a
  reason.
- Respects the documented conventions: behavior in the store layer, ownership checks for
  the destructive and restore paths.
- Decomposes into independently verifiable units with an executor per unit
  (test-first units for new behavior) and an explicit dependency order.
- Lists open questions with a recommended answer for each (for example whether hard-purge
  is ever needed).
- Produces no code and edits no files.

## Must not do

- Edit or create repository files.
- Cite files or functions that do not exist in the repo.
- Produce one monolithic unit or units without executors.
- Choose a design without naming a rejected alternative.
- Put ownership checks in route handlers against the documented convention.

## Score

- `pass`: evidence-cited scan, explicit decision with rejected alternative, executor-owned
  ordered units, open questions with recommendations, zero edits.
- `partial`: solid decomposition but evidence citations or the rejected alternative are
  thin.
- `fail`: implements anything, invents repo structure, or returns an unordered wish list.
