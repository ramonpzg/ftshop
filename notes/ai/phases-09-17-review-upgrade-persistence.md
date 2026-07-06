# Handover: phases 09-17, review, upgrade, and durable persistence

Written 2026-07-06 by the agent that reviewed and hardened the phase
00-08 scaffolding. Read CLAUDE.md first, then docs/architecture.md,
then this.

## What was built

**Durable canvas persistence (phases 09, 12).** The headline change.
The tldraw document no longer lives in browser IndexedDB. The backend
stores it at `data/canvas/snapshot.json` (atomic writes, one-step
rolling backup at `snapshot.prev.json`) behind `GET/PUT /canvas`, and
uploaded canvas assets land in `data/assets/` behind
`POST/GET/DELETE /canvas/assets`. Frontend side:
`ChessStudioCanvas.tsx` creates its own store with
`createTLStore({shapeUtils: [...defaultShapeUtils, ...custom],
bindingUtils: defaultBindingUtils, assets: backendAssetStore})`, loads
the server snapshot before mounting `<Tldraw>`, and saves document
changes through `actions/canvasSaveScheduler.ts` (debounce 800ms, one
save in flight, retry on failure, flush on visibilitychange). If the
initial snapshot fetch fails the canvas refuses to mount so a blank
document can never overwrite the real one. Storage is files, not
SQLite, so `just reset-db` and the deck are independent, and the deck
is committable to git. `just reset-canvas` deletes only the deck.

**Dependency sweep (phase 10).** tldraw 3.15 to 5.2.2, React 19.2,
Vite 8 (rolldown), TypeScript 6, Biome 2, Playwright 1.61; backend to
fastapi 0.139, pytest 9, httpx 0.28, ruff 0.15 (2026 style), ty
0.0.56. Migration notes in the phase 10 commit message.

**Slides (phase 11).** The Presentation page seeds eleven frame slides
matching docs/session-plan.md. `SlideControls.tsx` (bottom right)
steps through frames in name order via `calculations/slides.ts`;
PageUp/PageDown always work, arrows only when nothing is selected.

**Draft-first content (phase 14).** Seeded notes now follow the
session plan draft rather than the original build prompt: real-world
scenario mapping, the training ladder, draw-your-pieces exercise, the
narrator, the 100-prompts-to-LTX bridge, closing thoughts with merging.
Phosphor icons (`@phosphor-icons/react`) across panels. Mini IDE gained
Jinja chat-template and TRL LoRA training snippets and a dark
code-window look.

**Review fixes (phases 13, 15-17).** A 6-dimension multi-agent review
with adversarial verification found 45 confirmed issues. Fixed: stale
localStorage user after `just reset-db` soft-bricked clients (now 404 +
client-side recovery); `position_index` and `ply` allocated inside
their INSERT statements (join and move races produced duplicates);
presenter actions now reach all clients via a 3s poll
(`actions/presenterSync.ts`) with tldraw read-only enforcement for
attendees; presenter panel gated behind `?presenter=1`; reset-page
confirms; bring-to-view broadcasts the presenter's actual page; tldraw
fonts/icons/translations self-hosted via `@tldraw/assets` (offline
capable); illegal moves show reward -1 on the board; eval reruns
replace rows instead of stacking; replay fixture params sanitized
against path traversal; `JobOutput.cached` replaces the
isinstance(runner) sniff; canScroll on custom shapes; workspace zoom
capped at 100%; attendee list polls every 5s; image artifacts render
actual piece SVGs; em dashes purged from docs.

## Intentionally deferred, and why

- **tldraw sync (multiplayer canvas).** The store creation and save
  loop are exactly what `useSync` replaces; doing it now would have
  eaten the whole budget. Snapshot saving is last-write-wins if two
  browsers edit simultaneously; fine for one presenter, wrong for
  collaborative mode.
- **CodeMirror edits persist nowhere.** The IDE is editable because
  inspecting-by-editing is the point, but edits vanish on close. Needs
  a per-workspace snippet-override column if it matters.
- **Server-side enforcement of lock and ownership.** `make_move`
  accepts moves while locked; anyone can select snippets or run jobs on
  any workspace id. v0 has no auth, so enforcement would be theater;
  the sync-mode permissions layer is the real place for it.
- **Game-over surfacing.** `apply_move` knows checkmate; nothing tells
  the client the game ended. Post-game moves record as illegal
  (reward -1), which is at least pedagogically consistent.
- **Job param validation.** `POST /jobs` with fps=0 or negative counts
  500s and leaves an orphaned job_config row. The UI only sends fixed
  params, so this needs deliberate misuse.
- **`valid_json_rate` is tautological** (validates JSON the server
  itself serialized; always 1.0). It demonstrates the metric shape.
  A real version needs model outputs to judge.
- **Production serve mode.** 30 attendees on a cold Vite dev server
  works but is the slowest possible first load. A `just serve` recipe
  (vite build + preview, or FastAPI static) is cheap if wanted.
- **Attendee dedupe.** Joining from a second browser makes a second
  user with the same name. Harmless, clutters the attendee panel.
- **Model merging** exists only as a closing-slide line; the published
  abstract promises more.

## Known issues / tech debt

- `make_move` is not fully transactional: ply allocation is atomic
  now, but two simultaneous legal moves read the same `fen_before` and
  both record; the board ends on whichever lands last. Board is
  disabled client-side while a move is in flight, so this needs two
  devices on one workspace.
- `presenter_state.focused_user_id` is schema + API surface with no
  writer.
- `data/{raw,processed,tiny}` are empty scaffolding dirs.
- CloudRunner remains a stub by design.
- The canvas snapshot grows monotonically with authored content;
  nothing compacts or versions it beyond the one-step backup. Git is
  the intended history mechanism.

## What the next phase should tackle first

1. Fill the slide frames with real content and assets (human task, but
   agents may be asked to help layout).
2. `just serve` production mode for the venue.
3. tldraw sync spike: replace the store creation in
   ChessStudioCanvas with `useSync`, move the asset store URLs to
   absolute, keep everything else.
4. Real training path for page 2: generate the ~100 real-world
   scenario rows (session plan wants terse mappings of finished games
   to work/home/sports situations), push through the TRL snippet for
   real.

## Gotchas

- **`createTLStore` does not merge default shape utils.** Symptom:
  `Migration 'com.tldraw.binding.arrow/1' depends on missing migration`
  at store creation. Always spread `defaultShapeUtils` and pass
  `defaultBindingUtils`.
- **Vite 8 + @tldraw/assets:** the rolldown prebundler cannot load the
  package's `?url` imports; `optimizeDeps.exclude: ["@tldraw/assets"]`
  is required or the dev server dies on startup.
- **Fonts are module imports now.** Any test tooling that blocks
  `.woff2` requests (playwright route aborts) kills the entire module
  graph and yields a blank page. Do not block font URLs.
- **`bun test` must run from `web/`.** The happy-dom preload lives in
  `web/bunfig.toml`; from the repo root you get 57 mysterious DOM
  failures, and from `node_modules` you run tldraw's own test suite
  (3000+ tests, do not ask).
- **Biome 2 globs:** use folder form (`!**/dist`); the `/**` suffix
  triggers `useBiomeIgnoreFolder`, and `files.ignore` is gone.
- **tldraw 5 custom shapes:** augment `TLGlobalShapePropsMap` in
  `declare module "@tldraw/tlschema"`, type shapes as
  `TLShape<"workspace">`, implement `getIndicatorPath` returning a
  `Path2D` (JSX `indicator()` is a dead no-op), and use
  `editor.markEventAsHandled` instead of `stopEventPropagation`.
- **React 19 + RTL:** `@testing-library/dom` must be an explicit dev
  dependency.
- **e2e:** `playwright.config.ts` must point CHESS_STUDIO_CANVAS_DIR
  and CHESS_STUDIO_ASSETS_DIR at temp dirs or the suite overwrites the
  presenter's real deck. The persistent canvas accumulates workspace
  shapes across tests; scope locators to `.workspace-panel-own`.
- **Session state:** camera and current page are per-client
  (deliberately not saved to the server); the seeder only jumps to the
  Presentation page when it seeded something.
- **ty** is a 0.0.x preview; diagnostics move between versions. Pin
  loosely, expect churn.
