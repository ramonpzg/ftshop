# Local development

## Prerequisites

- [Bun](https://bun.sh) (frontend tooling)
- [uv](https://docs.astral.sh/uv/) (Python backend tooling, manages its
  own Python)
- `just` (command runner)

## First run

```
just install
just start
```

`just start` runs the backend (`uvicorn`, port 8000) and frontend
(`vite`, port 5173) together and stops both on Ctrl-C. Open
http://localhost:5173.

On backend startup the app initializes `euro_chess_studio.db` at the
repo root, seeds the five pages, and seeds the cached illustrative eval
numbers (Stockfish-dependent metrics, image/audio/video quality scores)
that don't have a live computation path in v0. This happens every
startup and is idempotent.

## Commands

| Command | What it does |
|---|---|
| `just install` | Install frontend and backend dependencies |
| `just start` | Run backend + frontend together |
| `just start-backend` / `just start-frontend` | Run just one side |
| `just test` | Backend `pytest` + frontend `bun test` (fast, no real browser) |
| `just test-backend` / `just test-frontend` | Run just one suite |
| `just test-e2e` | Playwright smoke tests against real backend + frontend processes |
| `just lint` | `ruff check` + Biome lint |
| `just typecheck` | `ty check` + `tsc --noEmit` |
| `just format` | `ruff format` + Biome format |
| `just reset-db` | Delete and recreate the local SQLite database (empty) |
| `just reset-canvas` | Delete the authored canvas snapshot (slides, shapes). Keeps uploaded assets |
| `just seed` | Re-populate pages and cached eval fixtures |
| `just install-audio` | Optional: local text-to-audio models (torch, transformers; several GB) |
| `just notebooks` | Export the marimo notebooks to in-browser WASM |

`just reset-db` followed by `just seed` is the fastest way back to a
clean demo state without restarting the backend. It never touches the
canvas: workshop state and authored slides reset independently.

## Canvas persistence

The tldraw document is not stored in the browser. It loads from the
backend on mount and saves back on every change, debounced. On disk:

- `data/canvas/snapshot.json` is the document. Commit it to version
  your slide deck. `snapshot.prev.json` is an automatic one-step
  backup and is gitignored.
- `data/assets/` holds files dropped onto the canvas (images, video,
  audio). Commit the ones you want to keep.

Stop the server, come back tomorrow, switch browsers, or serve the app
over the venue network: the deck is the same, because the file is the
source of truth. The status badge (top left) shows saving / saved /
save failed at all times. If the badge says save failed, the backend is
down; edits keep retrying until it comes back.

## Environment variables

Set these in your shell or in a repo-root `.env` file (loaded at backend
startup, never overriding the shell, never committed):

| Variable | For | Default |
|---|---|---|
| `OPENAI_API_KEY` | Model opponent and live analysis | unset (features disabled) |
| `OPENAI_BASE_URL` | Any OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Which model plays and comments | `gpt-5.5-mini` |
| `FAL_KEY` | Image and video generation on fal.ai | unset (generate disabled) |
| `HF_TOKEN` | Gated model downloads (stable-audio-open) | unset |

Swapping the opponent to a Hugging Face router later is a two-line .env
change: point `OPENAI_BASE_URL` at the router, set `OPENAI_MODEL`.

Everything degrades cleanly when unset: buttons disable with a hint,
nothing errors.

## Notebooks

Each technical page embeds a marimo notebook. Attendees run the WASM
export in their own browser; `just notebooks` builds those exports into
`web/public/notebooks/` (gitignored; sources live in `notebooks/`).
Rerun it after editing a notebook. Pyodide loads from its CDN on first
open, so warm it once before the session.

As the presenter you get a Browser / Live toggle on the panel: Live
embeds a locally running marimo server (`marimo edit notebooks/`,
default URL `http://localhost:2718`) with your real GPU behind it. If
the embed lags, the Open link pops it into its own tab.

Unsloth Studio: the mini IDE links to `http://localhost:8888`. Launch
it with `unsloth studio -p 8888`.

## tldraw license note

tldraw 4+ requires a license key for production domains only.
localhost and LAN serving (how this app runs at the workshop) need
nothing. If a copy ever goes up on a public domain, request tldraw's
free hobby license and keep the watermark, or buy a commercial key.

## Where things live

See `docs/architecture.md` for the actions/calculations/data split and
how the tldraw canvas and backend state relate. In short:

- Backend domain code: `api/src/euro_chess_studio/`
- Backend tests: `api/tests/` (mirrors the source layout)
- Frontend source: `web/src/`
- Frontend unit/component tests: `web/tests/`
- Frontend end-to-end tests: `web/e2e/`
- Cached job fixtures: `artifacts/cached/{text,image,audio,video}/`

## Testing notes

- Backend tests use a temporary SQLite file per test (`tmp_path`
  fixture), never the real `euro_chess_studio.db`.
- Frontend component tests run under Bun's test runner with
  `@happy-dom/global-registrator` for a DOM. They mock `fetch` at the
  network boundary rather than mocking application modules, so the
  real fetch-wrapper and action code always runs.
- Full tldraw `Editor` instances aren't created in component tests.
  happy-dom doesn't implement enough browser API surface (canvas
  contexts, ResizeObserver, IndexedDB) for that to work reliably. Real
  canvas interaction is covered by the Playwright e2e suite instead
  (see below), and by manual verification during development.
- Frontend e2e tests (`web/e2e/`) launch real backend and frontend
  processes via Playwright's `webServer` config, pointed at a scratch
  SQLite file in the OS temp directory so they never touch your local
  dev database. They exercise the same custom-shape
  double-click-to-edit interaction used throughout the app (see
  "Interacting with workspace shapes" below).

## Interacting with workspace shapes

Workspace and modality panels are custom tldraw shapes that only
accept pointer events while in **edit mode**, the same convention
tldraw's own video and embed shapes use. Double-click a panel to open
it, click elsewhere to close it. This is why `web/e2e/smoke.spec.ts`
double-clicks with `{ force: true }`: Playwright's default
actionability check refuses to double-click something with
`pointer-events: none`, which is correct outside edit mode but needs
bypassing to *enter* edit mode in an automated test, exactly as a real
double-click would.

## Known limitations (v0)

- No auth. Anyone can join with any name; "your workspace is
  read-only to others" is a client-side UI affordance, not a security
  boundary (see `docs/architecture.md`).
- No live multi-client sync. Two browsers both talking to the same
  backend will see each other's users and workspaces (real, not
  simulated), but there's no push channel, each client only sees
  updates when it re-fetches.
- Several eval metrics (centipawn loss, image/audio/video quality
  scores) are seeded from cached fixtures, not computed live, because
  they need infrastructure (Stockfish, a trained judge model) that's
  out of scope for v0. The UI marks these rows with a `cached` badge.
  Each fixture file also carries a `note` explaining why it's
  illustrative; the note stays in the fixture and is not shown in the
  UI yet.
- `CloudRunner` is a stub (`NotImplementedError`), no cloud job
  execution exists yet.
