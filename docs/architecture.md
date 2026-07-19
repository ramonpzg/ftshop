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

- `calculations/`, pure functions. FEN parsing, workspace grid layout,
  page seed content, dataset-shape labels. No fetch, no DOM, no tldraw
  editor. Fully unit-testable with plain inputs and outputs.
- `data/`, I/O boundaries: `data/api.ts` (the backend HTTP client) and
  `data/localUser.ts` (localStorage for the joined user's identity).
- `actions/`, things that mutate state or trigger behavior:
  `joinWorkshop`, `ensureWorkspaceShape`, `navigateToWorkspace`,
  `presenterSync`, `presenterNavigation`, `registerCanvasPermissions`.
  These are the only places that touch a live tldraw `Editor` instance
  to create, move, or guard shapes. Document seeding is no longer a
  client action; the sync server's migrations own it.
- `components/`, React components. They call actions and render data;
  they don't contain calculation logic themselves.

## The shared canvas: a sync room

The canvas document (pages, shapes, authored slides) is one shared
multiplayer room, hosted by a small Bun process (`web/sync-server/`)
running tldraw's own `TLSocketRoom` from `@tldraw/sync-core`. Clients
connect with `@tldraw/sync`'s `useSync` over a WebSocket at `/sync`,
proxied by the Vite dev server so every browser, localhost or LAN,
talks to the app's origin. Conflict resolution is per record inside
tldraw's sync engine (push/pull/rebase); two browsers editing at once
merge instead of overwriting each other. Clients hold no local
persistence: reload and reconnect always resume from the server
document, and offline edits rebase on top of it when the socket comes
back.

Durable state still belongs to the backend. At boot the sync server
loads `GET /canvas`, runs the canvas migrations (below), and refuses
to open the room if either fails, leaving the stored snapshot alone.
Every document change persists back through a debounced `PUT /canvas`.
The snapshot lives at `data/canvas/snapshot.json` in the same
`{store, schema}` format as before, written atomically with a one-step
rolling backup. Assets dropped onto the canvas (images, video, audio)
upload through a `TLAssetStore` to `POST /canvas/assets` and land in
`data/assets/`.

Files, not SQLite, on purpose: `just reset-db` wipes workshop state
between rehearsals without touching the deck, `just reset-canvas`
does the reverse (stop the stack first: the room holds the document in
memory), and both the snapshot and the assets can be committed to git
alongside the code.

The status badge separates liveness from durability: the room state
(connecting, live, offline retrying, sync failed) comes from the
WebSocket, and the canvas persistence state (saving, saved, save
failed retrying) is polled from the sync server's health endpoint, so
a dying backend is visible even while the room itself stays up. Stale
and conflicted are not states this design can produce, because a
reconnecting client rebases its changes instead of uploading a whole
stale document.

The backend also owns everything that must survive a canvas reset:
users, workspaces, moves, dataset rows, job configs, artifacts, eval
results, presenter state.

## Canvas ownership

Every page and shape carries its owner in `meta.owner`; no rule is
inferred from colors or labels. The presenter owns workshop structure
(pages, seeded content, slide frames, the deck and modality panels; a
record with no owner counts as presenter-owned). An attendee owns
their workspace shape and whatever they draw. The pure rules live in
`web/src/calculations/canvasOwnership.ts`; every client enforces them
on its own local changes through tldraw store side effects
(`registerCanvasPermissions`), so a normal attendee client cannot
delete or restructure authored content or another attendee's work.
At the socket, sessions that never identified a joined user connect
read-only. There is no authentication in v0: a hand-rolled hostile
client is out of scope and documented as such, unchanged from the
previous release.

## Canvas migrations

The document records its workshop version in the document record's
meta. Ordered, idempotent migrations
(`web/src/calculations/canvasMigrations.ts`) run on the sync server at
room load: ensure the five pages, ensure modality panels even on pages
that already have content, ensure the deck panel, stamp ownership.
Running twice is a no-op; legacy shape types that are still registered
(the notebook panel) pass through untouched; a thrown migration aborts
the room instead of overwriting the last valid snapshot. Documents the
runtime cannot represent are refused outright rather than half-loaded:
record or shape types absent from the schema, workshop versions above
the runtime's, and any schema sequence the runtime does not know all
fail with an actionable error while the disk snapshot stays intact. A
compatibility pre-step down-converts the three known tldraw 5.2.2
schema sequences (the runtime is pinned at 5.1.1). After migration and
before the room opens, every record runs through tldraw's own migrator
and the real validators (sync-server/schema.ts), so a malformed record
of a known type is caught at boot instead of reaching clients.

The two are linked by one convention: a workspace's tldraw shape id is
generated identically on both sides
(`shape:workspace-{userId}-{pageSlug}`, see
`calculations/ids.py` / `calculations/ids.ts`), but the frontend never
recomputes it, it always uses the id the backend returns for a
workspace. That keeps the two implementations from ever drifting apart
at runtime, while still letting either side own the generation logic
independently.

## Custom tldraw shapes

Four custom shape types exist. They are `BaseBoxShapeUtil` subclasses that
follow tldraw's own convention for embedded interactive content (the
same pattern its built-in video and embed shapes use): the shape's
HTML content only accepts pointer events while it's in *edit mode*
(double-click to open). Outside edit mode it's `pointer-events: none`
so tldraw's own canvas layer handles selection and dragging normally.

- `WorkspaceShapeUtil`, one per (user, page). Renders
  `WorkspacePanel`: chess board, dataset panel, mini IDE, config,
  artifact, and eval sections. Generated dynamically when a user joins
  or when the attendee panel needs to materialize a peer's workspace
  that this browser hasn't seen yet.
- `ModalityPanelShapeUtil`, one per non-text modality page (image,
  audio, video), seeded once alongside that page's starter content.
  Renders `ModalityPanel`: a config/artifact/eval trio, since those
  pages don't have per-user chess games to hang a full workspace off
  of.
- `DeckShapeUtil`, the Slidev iframe on the presentation page. The
  editable URL is browser-local so a presenter can point it at the
  machine hosting the deck; a localhost URL viewed from a LAN machine
  is rewritten at render time to the host the app was opened on
  (`calculations/deckUrl.ts`), so attendees see the presenter's deck
  rather than their own missing one.
- `NotebookShapeUtil`, compatibility support for old snapshots. New
  canvases do not seed it. It renders a standalone-Jupyter handoff
  rather than an iframe and can be removed after old snapshots no
  longer contain the shape.

## Backend: actions / calculations / data / jobs

- `chess/board.py`, the only place that touches `python-chess`
  directly. Legal-move checking and move application.
- `calculations/`, pure functions: the reward function, dataset row
  construction, eval metric math (legal move rate, valid JSON rate),
  the audio spectrogram toy calculation, video frame sampling.
- `data/`, one `sqlite3`-backed repository module per table. No
  business logic; only reads and writes.
- `actions/`, orchestration: `join_workshop`, `create_or_get_workspace`,
  `make_move`, `run_job`, the four presenter actions. These compose
  calculations and data-access calls and are what the routes call.
- `jobs/`, the job runner abstraction (see below).
- `routes/`, one FastAPI router per resource, thin: parse the
  request, call an action, serialize the result.

## Job runner

Three runner implementations behind one interface (`jobs/base.py`):

- `LocalRunner`, runs a small real calculation over the app's own
  data (e.g. `text.prompt_eval` reads a workspace's actual moves and
  computes legal-move-rate from them).
- `ReplayRunner`, loads a deterministic fixture from
  `artifacts/cached/{modality}/*.json` (e.g. `image.show_dataset`).
- `CloudRunner`, a stub. Raises `NotImplementedError`; no cloud
  execution exists in v0. It exists so a future remote runner has an
  interface to implement without touching the registry or the API.

`jobs/registry.py` is the only place that maps a job type to a runner.
Callers, the `run_job` action and the frontend, only ever say "run
job type X"; they never know or care which runner answered.

## Why some eval numbers are cached and some are computed

`GET /evals` returns rows with a `source` of either `computed` or
`cached`. `computed` rows come from real data (a workspace's actual
moves, run through `text.prompt_eval`). `cached` rows are seeded from
`artifacts/cached/{modality}/evals.json` on every backend startup.
These are the metrics that need infrastructure v0 doesn't have
(Stockfish for centipawn loss, a trained model to judge image style
consistency, and so on). Every cached fixture carries a `note`
explaining why it's illustrative. The eval panel renders whatever the
API returns; no component hardcodes a metric value.

## Presenter navigation

Presenter state carries an explicit navigation target: page slug,
optional frame id, camera bounds captured at click time, and a
monotonically increasing revision bumped by the backend on every
presenter-state change. Clients poll and order on the revision alone:
the first completed poll applies the current target (late joiners land
where the room is), afterwards only strictly newer revisions apply, so
repeated or slow polls can never move a camera backwards. Target
resolution is a pure calculation (`calculations/presenterTarget.ts`):
frame bounds first, captured bounds if the frame is gone, page fit
with a concise notice after that. The presenter's own camera is never
driven remotely.

## Network shape

Three processes on the workshop host: FastAPI (8000), the sync room
(8010), Vite (5173), plus Slidev (3030) when the deck runs. The two
dev servers bind the LAN and proxy everything a browser needs:
`/api` and `/sync` on 5173, `/api` on 3030. Browsers only ever talk to
the origin they loaded from; backend CORS lists just the documented
localhost development origins because proxied requests are
server-to-server, where CORS does not apply.
