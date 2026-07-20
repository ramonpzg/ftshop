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
  construction, the move vocabulary, eval metric math, model
  capability decisions (`model_catalog.py`), prompt construction and
  reply parsing, the audio spectrogram toy calculation, video frame
  sampling.
- `data/`, one `sqlite3`-backed repository module per table, plus the
  Chat Completions transport (`llm_client.py`). No business logic;
  only reads and writes. Repositories on the game path do not commit:
  the action that composes them owns the transaction.
- `actions/`, orchestration: `join_workshop`, `create_or_get_workspace`,
  `make_move`, `model_turn`, `suggest_scenario`, `run_job`, the four
  presenter actions. These compose calculations and data-access calls,
  decide what commits together, and are what the routes call.
- `jobs/`, the job runner abstraction (see below).
- `routes/`, one FastAPI router per resource, thin: parse the
  request, call an action, serialize the result.

### Transactions

`make_move` persists the move record, the board update, the dataset
rows, and any game outcome as one transaction; a failure rolls all of
it back, so a half-persisted move cannot exist. The model turn extends
this: the applied move and its attempt record commit together, while
failed attempts commit individually as they happen because a failed
reply is evidence that must survive the turn failing. The lazy timeout
check commits on its own; a flag fall is a fact about the wall clock,
not part of whichever action noticed it. `run_job` persists the job
config, the artifact, and any eval_results a handler wrote as one
transaction too; every repository on this path (`job_configs_repo`,
`artifacts_repo`, `eval_results_repo`) takes writes without committing,
so a failure between them (a provider error while building the
artifact, say) rolls back a job_config that would otherwise have no
matching artifact, and eval numbers computed by a run whose artifact
never landed.

### Turn ownership

In a timed match the participant always plays white and the configured
model answers as black; there is no color picker. `make_move` enforces
this server-side, not just by disabling the board: a participant move
submitted while an active game's fen shows black to move raises
`NotYourTurnError` (mapped to 409). Without it, a raw call to the
public move route (no `actor` parameter exists there; it always
defaults to `participant`) could play both colors, standing in for the
model, bypassing its recorded attempts and its unavailable/retry
recovery state, and polluting the participant's own legal-move-rate
and the exported dataset with moves the model was supposed to make.
Free play (no active game) has no such contract and is unrestricted;
model and fallback moves (`actor="model"`/`"fallback"`, only ever set
by `actions/model_turn.py`) are exempt by construction. The frontend
mirrors this: the board is only interactive on the participant's own
turn in an active game.

### The Chat Completions boundary

Every text-model call (opponent moves, scenario assessments, future
text jobs) goes through `data/llm_client.py`, which only ever calls
`/chat/completions`. Two typed settings profiles exist: `opponent`
(`OPENAI_*`) and `video_prompt` (`VIDEO_PROMPT_*` with documented
fallbacks), so local Gemma can play the board while hosted Luna writes
scenes in the same process without sharing endpoints, models, or
capabilities. Capability decisions (does this model accept
`reasoning_effort`, JSON mode) live in the typed catalog in
`calculations/model_catalog.py`, not in string checks at call sites.
The transport returns a `ChatOutcome` carrying content plus the
provenance callers persist: model, provider alias, attempt count,
request ids, and whether a capability fallback fired.

### Model attempts and the model turn

The `moves` table records what happened to the board, with an `actor`
column (participant, model, fallback; `unknown` for rows migrated from
before provenance existed). The `model_attempts` table records what
the model actually said: one immutable row per raw reply, with model,
provider alias, prompt version, ply, fen, parse and legality judgment,
request ids, and the applied move if one resulted. `actions/
model_turn.py` is an explicit state machine over those attempts:
transport failure, empty, unparsable, invalid syntax, illegal, stale
(the position changed while a reply was in flight), clock-expired (the
reply arrived after the game's clock ran out), or applied. After the
configured limit, a model that answered garbage is answered with a
deterministic fallback (first legal move in UCI order, actor
`fallback`), and a provider that never answered yields an explicit
`unavailable` outcome with a client-side retry. The board can never be
silently stuck on the model's turn.

The whole turn is bounded by one `MODEL_TURN_DEADLINE_SECONDS` overall
deadline (default 30s, comfortably under the 60s minimum game time
limit), not just by `MODEL_TURN_MAX_ATTEMPTS`: attempt count alone let
worst-case latency multiply unpredictably, since each attempt could
itself retry the HTTP call up to three times at up to
`MODEL_MOVE_TIMEOUT_SECONDS` (60s) each. The deadline is checked before
starting each attempt, and the last attempt's own timeout is capped to
whatever time remains, so total wall-clock time for a turn stays
predictable regardless of how transport retries stack. If the reply
does arrive but the clock has since expired, `make_move`'s clock check
raises before the move is applied; `model_turn` records that attempt
(status `clock_expired`) before the exception propagates, so a
legitimate -- possibly correct -- reply is never lost with zero
evidence just because the clock happened to run out in between.

### Scenario mappings

`scenario_assessments` persists the three-field real-world mapping
(assessment, real_world, video_prompt) per game and ply. The raw model
suggestion is written once and never updated; participant review
(accept or edit) fills separate final columns. Failed calls insert an
explicit failed row without touching prior records. Reload restores
the true latest state, including a failed one: `latest_scenario`
returns the newest row regardless of status, and the frontend renders
a failed reload exactly like a live failure (an explicit error with a
retry action), rather than silently reverting to an older suggestion
or the pristine empty state as if nothing had been attempted since the
game moved on. Recovery is asking again. Exports
(`chess_scenarios.jsonl`) carry both raw and approved values with
model, provider alias, and prompt version.

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
`cached`, and every row carries its provenance: numerator,
denominator, unit, direction, a definition sentence, a definition
version, the scope filters that produced the sample, and (for computed
rows) `model`, `checkpoint`, `run_id`, and `sample_ids` -- the frozen
input set as the exact move/attempt ids counted, not just descriptive
filters.

`computed` rows are real measurements with honest denominators:

- `legal_move_rate` counts one actor's recorded move attempts
  (participant by default). Model output and participant fumbling
  never share a denominator; rows migrated from before actor
  provenance existed are labelled `unknown` and excluded rather than
  guessed.
- `model_legal_move_rate` counts received model replies (from
  `model_attempts`) that contained a legal move. Transport failures
  stay out of the denominator because the model never answered; every
  retry counts; fallback moves are excluded by actor.
- `valid_json_rate` parses the stored raw replies of JSON-requesting
  tasks with the same extractor the app uses to consume replies. It
  measures model output, not the application's own serialization.

An empty sample is an explicit unavailable result: the eval job
reports it in its payload and *removes* any prior stored result for
that exact scope rather than persisting nothing and leaving the old
number on display. `text.prompt_eval` also accepts optional `model`
and `checkpoint` job params, threaded into the model-facing metrics;
`eval_results`' storage identity is `(modality, metric, workspace,
source, model, checkpoint)`, so a base and an adapted model's results
coexist as two rows instead of one overwriting the other, and a page
reset clears computed results for the workspaces it wipes. Every
metric from one `run_job` call shares a `run_id`. That is the
phase-34 before/after contract: same frozen input set (auditable via
`sample_ids`), both model versions identified and stored side by side.

`cached` rows are seeded from `artifacts/cached/{modality}/evals.json`
on every backend startup. These are the metrics that need
infrastructure v0 doesn't have (Stockfish for centipawn loss, a
trained model to judge image style consistency, and so on). Every
cached fixture carries a `note` explaining why it's illustrative, and
that note survives seeding, storage, the API, and rendering: the panel
shows it under the value, so a cached number can never pose as live.
The eval panel renders whatever the API returns; no component
hardcodes a metric value.

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
