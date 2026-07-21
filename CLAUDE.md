# euro-scipy-chess-studio

Interactive EuroSciPy 2026 workshop app for "Same Recipe, Different
Results: Fine-Tuning Models Across Modalities". A local-first tldraw
whiteboard with five pages (text, image, audio, video, plus a
presentation page), a separate Slidev deck, a standalone Jupyter
notebook, a chess domain throughout, and a FastAPI backend that owns
durable workshop state.

The repository is in pre-workshop hardening. `notes/comms/README.md`
contains the ordered phase prompts and current product decisions. Do not
assume `main` is already the release build.

## Commands

Everything goes through the Justfile. Do not add one-off scripts.

```
just install      # all core surfaces; use --whiteboard, --deck, --nb, etc. to limit it
just start        # backend :8000 + sync room :8010 + frontend :5173
just deck         # Slidev :3030
just session-notebook # standalone JupyterLab notebook
just room-url     # print the LAN URL attendees use
just test         # pytest + bun test
just test-e2e     # Playwright; uses its own browser discovery, override with CHESS_STUDIO_CHROMIUM
just lint         # ruff + biome
just typecheck    # ty + tsc
just format       # ruff format + biome format
just reset-db     # drop and recreate SQLite (workshop state only)
just reset-canvas # delete the authored canvas snapshot only
just seed         # repopulate pages and cached eval fixtures
```

## Layout

- `web/` React + tldraw frontend. Bun, Vite, TypeScript, Biome.
- `api/` FastAPI backend. uv, python-chess, ruff, ty.
- `data/` datasets (`raw/processed/tiny`), canvas snapshot, uploaded assets.
- `artifacts/` cached fixture JSON and generated job output.
- `deck/` Slidev presentation and Vue teaching components.
- `notebooks/full-session.ipynb` standalone Jupyter notebook.
- `docs/` architecture, session plan, demo plan, local dev, licenses.
- `notes/comms/` reviewed implementation prompts, in execution order.
- `notes/ai/` handover docs, one per phase. `notes/hu/` learning guides.

## Current product decisions

- The board, deck, and notebook are separate assets. Keep their visual
  languages separate: hand-drawn whiteboard, composed deck, pragmatic
  Jupyter notebook.
- The notebook is plain Jupyter. It is not Marimo and does not need an
  iframe or tldraw panel. Legacy Marimo sources and integration code may
  remain until the relevant reviewed phase removes them. Do not regenerate
  the old browser notebook exports.
- OpenAI-compatible text calls use `/chat/completions`, not the Responses
  API. `gpt-5.5-mini` does not exist. The current configurable default is
  `gpt-5.6-luna`.
- The local Gemma baseline is
  `google/gemma-4-E2B-it-qat-q4_0-gguf`. That GGUF is for deployment.
  Trainer examples use the matching
  `google/gemma-4-E2B-it-qat-q4_0-unquantized` weights and convert the
  merged result back to GGUF.
- Luna maps each game to a detailed real-world case and an LTX-ready scene
  prompt. The generated video stages that case. It does not depict a chess
  move, chessboard, or chess pieces.
- Preserve the narrowly bounded retry for the observed generic `401` text
  "You have insufficient permissions for this operation". The same key
  produced both `401` and `200` during key propagation. Do not generalize
  this to invalid, revoked, restricted, or denied credentials.
- The provisional teaching order is concise motivation, why chess, the
  chess basics needed by non-players, Ramon's route into it, outcome-first
  demos, and then decomposition of data, adaptation, and evaluation.

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

The latest direct instruction from Ramon wins. After that, current phase
decisions in `notes/comms/README.md` take precedence over older handovers
and plans. `docs/session-plan.md` remains the narrative source of truth,
but phase 34 will revise its order around outcome-first demos. The original
build prompt was scaffolding and does not override these sources.

Icons, when needed, come from Phosphor (`@phosphor-icons/react`).

## Git

`main` is the default branch locally and at `origin`. Work in phases, one
branch per phase, using the branch named in `notes/comms/`. Start a phase
from the accepted `main`, not from another unreviewed branch.

At the start of a phase:

1. Run `git status --short --branch` and confirm the base is understood.
2. If the tree contains work you did not create, do not stash, restore,
   resolve, or commit it. Stop and ask.
3. Create the phase branch before editing.

Commit throughout the phase, not only at the end. Each commit should be a
coherent development-log entry with its relevant focused checks passing.
Stage deliberately. Commit every source, test, fixture, migration, lockfile,
and document that belongs to the phase. Do not commit secrets, local databases,
build output, caches, or unrelated user work.

Push the phase branch so the work is recoverable and reviewable. Do not merge,
rebase, squash, or fast-forward it into `main` until Ramon has reviewed the
agent summary and diff. A phase is not ready for review with relevant
untracked or uncommitted files.

The final phase commit includes the required handover and learning guide. Use
detailed commit messages written like a development log. No co-authored-by
trailers.

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
