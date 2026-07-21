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

`just install` installs all four core surfaces. It deliberately excludes
model downloads and optional audio dependencies. Limit it when bandwidth or
time matters:

```
just install --whiteboard  # web + sync room + API
just install --web
just install --api
just install --deck
just install --nb          # root .venv for Zed and Jupyter
```

Flags can be combined. `just install --api --deck` installs only those two
surfaces. The Python and JavaScript installers use their committed locks.

`just start` runs the backend (`uvicorn`, port 8000), the canvas sync
room (Bun, port 8010), and the frontend (`vite`, port 5173) together
and stops all three on Ctrl-C. Open http://localhost:5173. Attendees
on the venue network use `just room-url` (the same Network URL Vite
prints); the dev server
proxies `/api` and `/sync` to the local backend and room, so nothing
else needs to be reachable from other machines.

On backend startup the app initializes `euro_chess_studio.db` at the
repo root, seeds the five pages, seeds the cached illustrative eval
numbers (Stockfish-dependent metrics, image/audio/video quality scores)
that don't have a live computation path in v0, and seeds the adaptation
fixtures: the reference training snapshot and the frozen held-out
evaluation suite, idempotent by content hash. This happens every
startup.

## Commands

| Command | What it does |
|---|---|
| `just install [flags]` | Install all core surfaces, or selected surfaces with `--whiteboard`, `--web`, `--api`, `--deck`, or `--nb` |
| `just start` | Run backend + sync room + frontend together |
| `just room-url` | Print the single LAN URL attendees open |
| `just start-backend` / `just start-frontend` / `just start-sync` | Run just one piece |
| `just test` | Backend `pytest` + web and deck `bun test` (fast, no real browser) |
| `just test-backend` / `just test-frontend` | Run just one suite |
| `just test-e2e` | Playwright multi-client suite; uses Playwright's own browser cache, `CHESS_STUDIO_CHROMIUM` overrides the executable |
| `just lint` | `ruff check` + Biome lint |
| `just typecheck` | `ty check` + `tsc --noEmit` |
| `just format` | `ruff format` + Biome format |
| `just reset-db` | Delete and recreate the local SQLite database (empty) |
| `just reset-canvas` | Delete the authored canvas snapshot (slides, shapes). Keeps uploaded assets |
| `just seed` | Re-populate pages and cached eval fixtures |
| `just install-audio` | Optional: local text-to-audio models (torch, transformers; several GB) |
| `just make-media` | Regenerate the committed workshop media fixtures (deterministic; installs the small `media` extra) |
| `just deck` | The Slidev deck on port 3030 |
| `just session-notebook` | Open the standalone Jupyter notebook in JupyterLab |
| `just mock-llm` | Fake OpenAI endpoint with configurable latency, for rehearsal |
| `just load-test` | Simulate a room of attendees against a running backend |

`just reset-db` followed by `just seed` recreates SQLite without restarting
the backend. It never touches the canvas. That separation also means it is
not the right last-minute cleanup once real workspace shapes exist: those
shapes would keep user ids the new database no longer knows. Use the
presenter panel's page reset for game data. Pair `reset-db` with an intentional
canvas reset only when rebuilding the room from scratch.

## The shared room and canvas persistence

The tldraw document is one multiplayer room hosted by the sync server
(`web/sync-server/`, tldraw's TLSocketRoom). Browsers connect over a
WebSocket at `/sync` and edit the same document; conflicts resolve per
record, so concurrent attendees merge instead of overwriting each
other. Reload and reconnect always resume from the server document.
Nothing is persisted in the browser.

Ownership is enforced in every client: attendees can edit their own
workspace and drawings, and cannot delete or restructure the
presenter's pages, frames, notes, or panels. The presenter client
(?presenter=1) can edit everything. Before joining, a session is
read-only at the socket.

The sync server loads the document from the backend at boot, runs the
canvas migrations, and persists every change back, debounced. On disk:

- `data/canvas/snapshot.json` is the document. Commit it to version
  your slide deck. `snapshot.prev.json` is an automatic one-step
  backup and is gitignored.
- `data/assets/` holds files dropped onto the canvas (images, video,
  audio). Commit the ones you want to keep.

Stop the stack, come back tomorrow, switch browsers, or serve the app
over the venue network: the deck is the same, because the server owns
the truth. The status badge (top left) shows two separate facts. Room
state: connecting, live, offline (retrying), sync failed; stale and
conflicted cannot occur under the sync engine's rebase model. Canvas
persistence, polled from the sync server: saving, saved, or save
failed (retrying). "Room: live" only means the WebSocket is up; if the
backend dies, the room keeps serving clients while the badge reads
"Canvas: save failed, retrying" until disk writes succeed again. A
sync server asked to shut down with unsaved changes retries briefly,
then exits nonzero and says so.

`just reset-canvas` deletes the snapshot files. Run it with the stack
stopped: the room holds the document in memory and would immediately
persist it right back.

The Presentation page remains in the canvas as an emergency embedded-deck
fallback, but it is intentionally absent from the normal page tabs. The deck
and notebook are the primary presentation surfaces.

## Environment variables

Set these in your shell or in a repo-root `.env` file (loaded at backend
startup, never overriding the shell, never committed):

| Variable | For | Default |
|---|---|---|
| `OPENAI_API_KEY` | Model opponent and live analysis | unset (features disabled) |
| `OPENAI_BASE_URL` | Any OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Analysis and the default opponent | `gpt-5.6-luna` |
| `OPPONENT_MODELS` | Extra opponents in the Start game picker, comma-separated | unset (default model only) |
| `OPPONENT_ENDPOINT_IS_LOCAL` | Set to `1` to attest the opponent endpoint is a local model on the room's own hardware; a loopback `OPENAI_BASE_URL` counts automatically. The budget half of the attendee gate | unset (fail closed for attendees) |
| `ROOM_MODEL_PLAY` | Set to `1` to open attendee timed games and model replies, after `just load-test 40` against the real endpoint showed model-move p95 inside the turn deadline. The capacity half of the attendee gate; locality alone never opens the room | unset (attendees free-play; inference is presenter-led) |
| `VIDEO_PROMPT_API_KEY` | Scene-writing calls when the opponent runs elsewhere | falls back to `OPENAI_API_KEY` |
| `VIDEO_PROMPT_BASE_URL` | Scene-writing endpoint | falls back to `OPENAI_BASE_URL` |
| `VIDEO_PROMPT_MODEL` | Scene-writing model | `gpt-5.6-luna` |
| `MODEL_TURN_MAX_ATTEMPTS` | Model-turn retries before the deterministic fallback | 2 (clamped 1-5) |
| `MODEL_TURN_DEADLINE_SECONDS` | Overall wall-clock budget for one model turn, regardless of attempt count | 30 (clamped 5-120) |
| `BENCHMARK_RUN_DEADLINE_SECONDS` | Overall wall-clock budget for one live benchmark run; unreached examples are recorded as failures | 60 (clamped 10-300) |
| `OPENAI_RECENT_KEY_401_RETRY` | Set to `1` right after creating or rotating a key: allows one or two retries of the exact generic-permissions 401 seen during key propagation | unset (401 fails immediately) |
| `FAL_KEY` | Image and video generation on fal.ai | unset (generate disabled) |
| `HF_TOKEN` | Gated model downloads (stable-audio-open) | unset |

The key and the base URL travel together. An OpenRouter key against
the default api.openai.com returns 401, which the board reports as a
model error the moment you start a game. For OpenRouter, set all
three, plus the picker for the small-vs-frontier demo:

```
OPENAI_API_KEY=sk-or-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/<frontier-model-id>
OPPONENT_MODELS=google/<small-model-id>,openai/<frontier-model-id>
```

Model ids follow the endpoint's naming: OpenRouter wants
`provider/model` (check the exact Gemma id in their registry),
api.openai.com wants bare names. When OPPONENT_MODELS lists more than
one model, Start game grows a picker; each match remembers its
opponent, and start over keeps it. Every entry resolves against the
one `OPENAI_BASE_URL` and key: a picker spanning a local llama.cpp
and a hosted endpoint at the same time needs per-model endpoints,
which is the phase 4b named-profile registry, not this table.

The room policy fails closed on top of this. A browser that is not on
the presenter's machine can only start timed games or trigger model
replies when the opponent endpoint is known local (loopback base URL,
or the attestation above) and `ROOM_MODEL_PLAY=1` is set after the
real-endpoint load test. Solo development on one laptop is loopback
and never notices; a phone on your LAN pointed at the dev server gets
free play until you set both, which is the intended behavior, not a
bug. Locality and capacity are separate gates because they fail
differently: a hosted endpoint burns money, a local one queues forty
requests behind one server until every turn deadline expires.

The shared text client calls `/chat/completions`. It does not use the
Responses API. It retries rate limits, server failures, and transport
failures with backoff and Retry-After. The narrowly bounded retry for
the generic permissions `401` observed while a new project key was
propagating now needs evidence: the same credential already succeeded
in this process, or `OPENAI_RECENT_KEY_401_RETRY=1` was set after
creating or rotating a key. Explicit invalid-key and access-denial
responses fail immediately. Errors retain every provider request ID.
Model capabilities live in a typed catalog: local Gemma through
llama.cpp never receives `reasoning_effort`, hosted Luna does, and a
provider that rejects `response_format` or `reasoning_effort` by name
gets one retry without that field, recorded in attempt provenance.

If the model opponent starts answering garbage during a session, the
board does not stall: after `MODEL_TURN_MAX_ATTEMPTS` failed replies
the game plays the first legal move in UCI order, recorded as a
fallback rather than a model move. If the provider cannot be reached
at all, the turn reports itself unavailable and the workspace offers
a retry button. Rehearse both with the mock LLM's `--move-mode
illegal` and `--move-mode invalid` flags.

Everything degrades cleanly when unset: buttons disable with a hint,
nothing errors.

## Notebook

`notebooks/full-session.ipynb` is a standalone Jupyter notebook. It is
not served by Vite, exported to browser WASM, or required inside a
tldraw panel. Open it separately with `just session-notebook` when the
run of show calls for it.

The repository still contains legacy Marimo sources, generated output
inside the converted notebook, and frontend notebook-panel code. They
are not the active notebook workflow. Do not run the removed export
commands or treat those files as a reason to restore the iframe. Their
cleanup belongs in a reviewed phase after the notebook content settles.

Unsloth Studio: the mini IDE links to `http://localhost:8888`. Launch
it with `unsloth studio -p 8888`.

## Load testing the room

Before trusting the laptop with 40 people, make it survive 40 fake
ones. Three terminals:

```
just mock-llm                 # OpenAI-shaped endpoint, 1.2s per reply
OPENAI_API_KEY=test OPENAI_BASE_URL=http://127.0.0.1:9999 just start-backend
just load-test 40 60          # 40 attendees for 60 seconds
```

Each simulated attendee behaves like the real UI: joins, starts a
timed match, plays legal moves with think time, asks the model for
black's replies (retrying an open model turn the way the UI's retry
button does), and polls presenter state every three seconds.
Assessments are not part of the workload: since the room model policy
they are manual, presenter-only, one per beat, so simulating one per
exchange would double model traffic the real room never produces. The
report at the end shows per-endpoint latency percentiles, error
counts (every non-2xx response and every transport failure), the
model-turn outcome tally, and an explicit PASS/FAIL verdict on
whether the run certifies ROOM_MODEL_PLAY; docs/demo-plan.md has the
workflow. On a 4-core container, 40 attendees run error free: board
moves at ~20ms p50, model-bound calls at the mock's latency plus
about a second of queueing. Numbers on a real laptop should be
better.

Two notes on what makes this hold up: SQLite runs in WAL mode with a
busy timeout (readers do not block on writers, and colliding writers
queue instead of throwing), and the sync-route thread pool is raised
to 120 because every in-flight model call holds a worker thread for
its whole round trip.

## The presenter dashboard

The presenter panel (open the app with `?presenter=1`) has a Games
section: every match in the room, active first, with the player's
name, a countdown or a result, and the move count, refreshed every
three seconds. Below it, two buttons:

- **Download SFT dataset**: prompt/completion pairs
  (`chess_sft.jsonl`), what the training snippets load.
- **Download all shapes**: the instructor's archive
  (`chess_all_shapes.jsonl`), every sample from every game across all
  six dataset shapes, each line tagged with its shape and workspace.
  This is the file to take to the GPU.

Both export on click and open the file in a new tab. Attendees can
still export their own view; these two collect the whole room.

## The deck

The workshop has three assets with separated concerns: the board is
where the room works, the deck is where the narrative lives, the
notebook is the fallback and the take-home.

`just deck` runs the Slidev deck on port 3030. The Presentation page
of the board embeds it in a panel (double-click to drive it; the Open
link pops it into its own tab, which is where presenter mode and
speaker notes live). The panel's URL is editable per browser if the
deck runs elsewhere.

The deck's content plan, slide by slide, with image prompts and
component notes, is `docs/deck-plan.md`. Slides live in
`deck/slides.md`; the Vue components (the live room dashboard, the
dataset shape cycler, the reward meter, the modality grid) are in
`deck/components/`. LiveRoom talks to the backend through the deck's
own `/api` proxy (`deck/vite.config.ts`), so it works from port 3030
and from LAN machines. Backend down before any data shows a terse
offline hint; down after data keeps the stale list visible with a
reconnecting note. The Slidev server binds the LAN; an attendee
viewing the embedded deck panel gets the presenter's hostname
substituted automatically when the stored URL points at localhost.

## The standalone notebook

`notebooks/full-session.ipynb` contains the end-to-end material in a
plain Jupyter format. `just session-notebook` opens JupyterLab through
the API environment. Optional provider and local-model cells still
depend on their documented credentials and packages.

The notebook can use `data/processed/text/chess_sft.jsonl` when the app
has exported it. It is a pragmatic presenter and take-home asset, not a
required application fallback or a browser integration. Notebook
content will receive its own review after the five hardening phases.

## tldraw version pin

The tldraw stack is pinned at 5.1.1 across `tldraw`, `@tldraw/sync`,
and `@tldraw/sync-core` because the sync protocol and store schema
must share one version. `@tldraw/assets` stays at 5.2.2 (static URL
maps only). If you upgrade, move every tldraw package in one commit
and check the canvas migration pre-step in
`web/src/calculations/canvasMigrations.ts`: it knows the exact schema
sequences that differ between 5.1.1 and 5.2.2 and refuses anything
newer it cannot prove safe. The same policy applies to record and
shape types, unknown schema sequences, and workshop versions above the
runtime's: refuse to load with an actionable error instead of opening
a room that clients cannot render. Before the room opens, every
migrated record is also validated through the real tldraw validators,
so a structurally broken record of a known type fails at boot too. In
every case the disk snapshot stays untouched.

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
- Frontend e2e tests (`web/e2e/`) launch the real backend, sync room,
  and frontend via Playwright's `webServer` config, pointed at scratch
  SQLite and canvas directories in the OS temp directory so they never
  touch your local state. `room.spec.ts` drives two and three browser
  contexts against one room for the multi-client acceptance cases;
  `smoke.spec.ts` covers the single-client basics, including the
  custom-shape double-click-to-edit interaction (see "Interacting with
  workspace shapes" below).
- The e2e stacks pin `OPENAI_API_KEY`, `VIDEO_PROMPT_API_KEY`,
  `FAL_KEY`, and `OPPONENT_MODELS` to empty strings, so whatever
  credentials your shell or a repo-root `.env` carries cannot leak in
  and change what the app under test offers (a live-benchmark button
  appearing because your personal key was inherited, for example).
  Tests that need credential-dependent behavior must set their own
  values explicitly.
- Playwright discovers its browser from its own cache by default. Set
  `CHESS_STUDIO_CHROMIUM` to point at a specific executable (the old
  hardcoded `/opt/pw-browsers/chromium` machine sets exactly that).
  The complete release command surface is phase 36's item.

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

- No auth. Anyone can join with any name, and anyone who adds
  `?presenter=1` gets presenter rights. Ownership rules are enforced
  in every normal client and unidentified sessions are read-only at
  the socket, but a hand-rolled WebSocket client could bypass the
  per-shape rules. That is an accepted boundary for a room of workshop
  attendees, not a security model. The one server-enforced line: the
  room model policy. All generation (image, video, audio including
  local synthesis, live benchmarks), position assessments, and
  non-default opponent picks are refused with a 403 for any client
  that is not on the presenter's machine, so presenter rights on the
  canvas never include spending the provider budget or the
  presenter's GPU from an attendee laptop. The check trusts only the
  last X-Forwarded-For hop, and the dev proxies overwrite the header
  with the peer address, so a client-supplied "127.0.0.1" prefix does
  not spoof it.
- One room. The sync server hosts a single workshop document; there is
  no room routing and no need for it.
- The sync server's in-memory clock resets on restart; clients
  resynchronize from scratch when it comes back, which is invisible
  beyond a brief reconnect.
- Several eval metrics (centipawn loss, image/audio/video quality
  scores) are seeded from cached fixtures, not computed live, because
  they need infrastructure (Stockfish, a trained judge model) that's
  out of scope for v0. The UI marks these rows with a `cached` badge
  and renders each fixture's `note` under the value, so a cached
  number can never pose as live.
- Adapter training is a cached replay bound to the reference snapshot
  by content hash; there is no live training path, and the panel's
  banner says it plainly: scripted illustration, no model was trained.
  The 409 refusals enforce the same honesty. The adapted checkpoint
  has no live serving path either (serving it would need a merge and
  GGUF conversion), so its benchmark runs are always replayed and
  labelled "replayed (scripted)".
- `CloudRunner` is a stub (`NotImplementedError`), no cloud job
  execution exists yet.
