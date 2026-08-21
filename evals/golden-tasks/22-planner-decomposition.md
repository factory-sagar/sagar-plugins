# Golden Task 22: Planner Decomposition with Repo Evidence

Version: 2

## Target

`planner`.

## Intent

Deliver an evidence-anchored, implementation-free plan for soft-delete and restore that scans
the real territory, makes and justifies a representation decision against a rejected
alternative, respects the store-layer and ownership conventions, sequences executor-owned
test-first units, and resolves open questions with recommendations; invented repository
structure or implementation work misses this goal.

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

## Fulfillment

- Cites `src/routes/notes.js`, `src/store/notes.js`, and `docs/conventions.md` with the
  behavior each contributes to the territory scan.
- Explicitly chooses a soft-delete representation (such as `deletedAt` versus a separate
  collection) and records a rejected alternative with a reason.
- Keeps behavior in the store layer and ownership checks on the destructive and restore paths.
- Decomposes the work into independently verifiable, executor-owned units, including
  test-first units for new behavior, in an explicit dependency order.
- Lists open questions, such as whether hard-purge is needed, with a recommended answer for each.
- Produces an implementation-free plan without repository edits.

## Boundaries

- Edit or create repository files.
- Cite files or functions that do not exist in the repo.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
