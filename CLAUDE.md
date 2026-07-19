# euro-scipy-chess-studio

Interactive EuroSciPy 2026 workshop app for "Same Recipe, Different
Results: Fine-Tuning Models Across Modalities". A local-first tldraw
whiteboard with five pages (text, image, audio, video, plus a
presentation page), a chess domain throughout, and a FastAPI backend
that owns all durable state.

## Commands

Everything goes through the Justfile. Do not add one-off scripts.

```
just install      # bun install + uv sync
just start        # backend :8000 + frontend :5173
just test         # pytest + bun test
just test-e2e     # playwright smoke tests (needs both servers down)
just lint         # ruff + biome
just typecheck    # ty + tsc
just format       # ruff format + biome format
just reset-db     # drop and recreate SQLite (workshop state only)
just seed         # repopulate pages and cached eval fixtures
```

## Layout

- `web/` React + tldraw frontend. Bun, Vite, TypeScript, Biome.
- `api/` FastAPI backend. uv, python-chess, ruff, ty.
- `data/` datasets (`raw/processed/tiny`), canvas snapshot, uploaded assets.
- `artifacts/` cached fixture JSON and generated job output.
- `docs/` architecture, session plan, demo plan, local dev, licenses.
- `notes/ai/` handover docs, one per phase. `notes/hu/` learning guides.

## Architecture rules

Read `docs/architecture.md` before changing structure. The rules that
matter most:

- Actions, calculations, and data access stay separate on both sides.
  Calculations are pure. Data access (SQLite repos, file stores) holds
  no business logic. Actions orchestrate.
- No core logic inside React components. Components call actions and
  render data.
- The backend owns durable workshop state (users, workspaces, moves,
  dataset rows, jobs, artifacts, evals, presenter state). The canvas
  document and its assets are persisted through the backend too, on
  disk under `data/`, so authored content survives anything short of
  deleting the repo.
- The frontend never knows which job runner handled a job.
- Real tests only. Temp databases and real calculations, no
  assert-true filler, no mocking the whole system.

## Copy style

All visible UI copy and docs follow Ramon's style. Direct. Terse.
Practical. No emojis. No em dashes. No marketing fluff. No fake
enthusiasm. Short labels with clear verbs: "Train", "Evaluate",
"Show dataset", "Reveal artifact".

## Content source of truth

When the original build prompt and `docs/session-plan.md` disagree,
the session plan wins. It captures Ramon's mental model of the session;
the prompt was scaffolding instructions.

Icons, when needed, come from Phosphor (`@phosphor-icons/react`).

## Git

Work in phases, one branch per phase, detailed commit messages written
like a development log. No co-authored-by trailers.

## End-of-phase documentation

Every phase ends with two documents. Do not skip these.

### Handover docs (notes/ai/)

Written at the end of each phase by the agent that completed it. Must include:
- What was built (features, files, architectural decisions).
- What was intentionally deferred and why.
- Known issues or tech debt.
- What the next phase should tackle first.
- Any gotchas the next agent should know (platform quirks, library bugs, fragile areas).

### Learning guides (notes/hu/)

Written at the end of each phase for the human. The ratio is roughly 40% Socratic questions / 60% guided walkthrough.

The Socratic portions ask the human to think through decisions: "Why did we separate EpisodePlaybackState from Episode? What would break if they were one table?" The walkthrough portions explain the codebase with concrete examples, code snippets, and a narrative that teaches how the pieces connect.

**Tone for guides:** flowing prose, no bullet-point dumps or excessive colons or semi-colons, absolutely no emojis. Terse, direct, and to 
the point with sporadic wit and subtle hints of sarcasm that catches anyone off guard. Favour "use" over "utilise." Never say delve, dive 
in, or extraordinary. Imagine explaining the work to Richard Feynman and Ali Wong simultaneously. Precise enough for a physicist, 
entertaining enough for a comedian.
