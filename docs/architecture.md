# Architecture

## Shape of the system

```
web/          React + tldraw frontend (Bun, Vite, TypeScript)
api/          FastAPI backend (uv, python-chess)
data/         Dataset fixtures (raw / processed / tiny)
artifacts/    Cached fixture JSON and generated job output
docs/         This directory
```

Two independent processes talk over HTTP: the backend owns all durable
state in SQLite, the frontend owns the tldraw canvas. Neither embeds the
other. `just start` runs both.

## Frontend: actions / calculations / data

`web/src/` is split the same way the brief asks for on the backend:

- `calculations/` — pure functions. FEN parsing, workspace grid layout,
  page seed content, dataset-shape labels. No fetch, no DOM, no tldraw
  editor. Fully unit-testable with plain inputs and outputs.
- `data/` — I/O boundaries: `data/api.ts` (the backend HTTP client) and
  `data/localUser.ts` (localStorage for the joined user's identity).
- `actions/` — things that mutate state or trigger behavior:
  `joinWorkshop`, `ensureWorkspaceShape`, `navigateToWorkspace`,
  `seedTldrawDocument`. These are the only places that touch a live
  tldraw `Editor` instance to create or move shapes.
- `components/` — React components. They call actions and render data;
  they don't contain calculation logic themselves.

## The tldraw canvas vs. backend state

The canvas document (pages, shapes, authored slides) is persisted
through the backend. On mount the frontend fetches the saved snapshot
from `GET /canvas`, loads it into a store it creates itself, and then
saves every document change back with a debounced `PUT /canvas`. The
snapshot lives at `data/canvas/snapshot.json`, written atomically with
a one-step rolling backup. Assets dropped onto the canvas (images,
video, audio) upload through a `TLAssetStore` to `POST /canvas/assets`
and land in `data/assets/`.

Files, not SQLite, on purpose: `just reset-db` wipes workshop state
between rehearsals without touching the deck, `just reset-canvas`
does the reverse, and both the snapshot and the assets can be
committed to git alongside the code. Because the source of truth is on
the server, the presenter's authored content survives dev-server
restarts and browser or machine changes, and attendees connecting over
the venue network see the same document.

If the initial snapshot fetch fails, the canvas refuses to mount and
saving stays disabled, so a freshly seeded fallback document can never
overwrite the real one. The status badge shows saving / saved / save
failed at all times.

The backend also owns everything that needs to survive a canvas reset
or be shared across a real multi-client future: users, workspaces,
moves, dataset rows, job configs, artifacts, eval results, presenter
state.

The two are linked by one convention: a workspace's tldraw shape id is
generated identically on both sides
(`shape:workspace-{userId}-{pageSlug}`, see
`calculations/ids.py` / `calculations/ids.ts`), but the frontend never
recomputes it — it always uses the id the backend returns for a
workspace. That keeps the two implementations from ever drifting apart
at runtime, while still letting either side own the generation logic
independently.

## Custom tldraw shapes

Two custom shape types exist, both `BaseBoxShapeUtil` subclasses that
follow tldraw's own convention for embedded interactive content (the
same pattern its built-in video and embed shapes use): the shape's
HTML content only accepts pointer events while it's in *edit mode*
(double-click to open). Outside edit mode it's `pointer-events: none`
so tldraw's own canvas layer handles selection and dragging normally.

- `WorkspaceShapeUtil` — one per (user, page). Renders
  `WorkspacePanel`: chess board, dataset panel, mini IDE, config,
  artifact, and eval sections. Generated dynamically when a user joins
  or when the attendee panel needs to materialize a peer's workspace
  that this browser hasn't seen yet.
- `ModalityPanelShapeUtil` — one per non-text modality page (image,
  audio, video), seeded once alongside that page's starter content.
  Renders `ModalityPanel`: a config/artifact/eval trio, since those
  pages don't have per-user chess games to hang a full workspace off
  of.

## Backend: actions / calculations / data / jobs

- `chess/board.py` — the only place that touches `python-chess`
  directly. Legal-move checking and move application.
- `calculations/` — pure functions: the reward function, dataset row
  construction, eval metric math (legal move rate, valid JSON rate),
  the audio spectrogram toy calculation, video frame sampling.
- `data/` — one `sqlite3`-backed repository module per table. No
  business logic; only reads and writes.
- `actions/` — orchestration: `join_workshop`, `create_or_get_workspace`,
  `make_move`, `run_job`, the four presenter actions. These compose
  calculations and data-access calls and are what the routes call.
- `jobs/` — the job runner abstraction (see below).
- `routes/` — one FastAPI router per resource, thin: parse the
  request, call an action, serialize the result.

## Job runner

Three runner implementations behind one interface (`jobs/base.py`):

- `LocalRunner` — runs a small real calculation over the app's own
  data (e.g. `text.prompt_eval` reads a workspace's actual moves and
  computes legal-move-rate from them).
- `ReplayRunner` — loads a deterministic fixture from
  `artifacts/cached/{modality}/*.json` (e.g. `image.show_dataset`).
- `CloudRunner` — a stub. Raises `NotImplementedError`; no cloud
  execution exists in v0. It exists so a future remote runner has an
  interface to implement without touching the registry or the API.

`jobs/registry.py` is the only place that maps a job type to a runner.
Callers — the `run_job` action and the frontend — only ever say "run
job type X"; they never know or care which runner answered.

## Why some eval numbers are cached and some are computed

`GET /evals` returns rows with a `source` of either `computed` or
`cached`. `computed` rows come from real data (a workspace's actual
moves, run through `text.prompt_eval`). `cached` rows are seeded from
`artifacts/cached/{modality}/evals.json` on every backend startup —
these are the metrics that need infrastructure v0 doesn't have
(Stockfish for centipawn loss, a trained model to judge image style
consistency, and so on). Every cached fixture carries a `note`
explaining why it's illustrative. The eval panel renders whatever the
API returns; no component hardcodes a metric value.

## Collaborative sync readiness

v0 is local single-user, but the domain model doesn't assume it:
- Every workspace has an explicit `user_id` owner, checked client-side
  (`CurrentUserContext`) to style someone else's workspace read-only.
  This is **not** an enforcement boundary — v0 has no auth, so it's
  purely a UI affordance modeling what a sync-aware permissions layer
  would need to check server-side later.
- Presenter state (`presenter_state` table) is a single source of
  truth already separate from any one client's local state, ready to
  be broadcast over a sync channel instead of just polled.
- The tldraw canvas is a swappable persistence layer: today the app
  creates its own store, loads the server snapshot, and saves changes
  back over HTTP. tldraw sync replaces exactly that store-creation
  and save loop with a synced store; shapes, actions, and components
  stay untouched. The asset store is already the shape sync expects.
