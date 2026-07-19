# Handover: phase 32, room correctness

Written 2026-07-19 on branch `phase-32-room-correctness`. The four
release blockers from the review: whole-snapshot overwrites, page-only
presenter navigation, the deck's broken network path, and
seed-only-when-empty. All four are fixed and covered by tests,
including real multi-browser Playwright runs.

## The synchronization design

The canvas is now a real multiplayer room using tldraw's own sync
stack: `useSync` (`@tldraw/sync`) in the browser, `TLSocketRoom`
(`@tldraw/sync-core`) in a small Bun process at `web/sync-server/`,
port 8010. Clients connect over `/sync`, proxied by the Vite dev
server, so LAN attendees stay on the app's origin and no extra port
needs to be reachable. Conflicts resolve per record in the engine's
push/pull/rebase model. Clients keep no local persistence; reload and
reconnect resume from the server document.

The backend remains the owner of durable state. The sync server boots
by fetching `GET /canvas`, migrating, and persisting changes back
through `PUT /canvas` with the same debounced save scheduler the
browser used to run (`web/src/actions/canvasSaveScheduler.ts`, now a
server module in practice). The on-disk format is unchanged
(`{store, schema}` at `data/canvas/snapshot.json` with the rolling
backup), so reset-canvas, git versioning, and the backup restore
procedure all survive. If the backend is unreachable at boot or a
migration throws, the server exits nonzero and touches nothing.

### Rejected options

- Keeping HTTP snapshots with ETags/409: a normal concurrent edit
  would still lose someone's work on retry; the review explicitly
  rules this out.
- A hand-rolled operation log or partial CRDT: the review explicitly
  rules this out too, and tldraw ships a proven engine.
- Hosting the room inside FastAPI: the sync engine is TypeScript;
  reimplementing its protocol in Python is the partial-CRDT trap with
  extra steps. The Bun sidecar keeps protocol code upstream and
  persistence behind the existing backend boundary.
- tldraw's SQLiteSyncStorage: would move document ownership into the
  sync process. InMemory room + PUT /canvas keeps the backend the only
  writer of durable state.

### The version pin (important)

This environment is offline; its package cache holds `@tldraw/sync`
and `@tldraw/sync-core` only at 5.1.1, so the whole tldraw stack is
pinned to 5.1.1 (`@tldraw/assets` stays 5.2.2, static URL maps only,
no runtime code). The authored snapshot was saved by tldraw 5.2.2,
whose schema is one step ahead in exactly three sequences. A
compatibility pre-step in the canvas migrations down-converts them
losslessly for the content this app produces (note:
textLastEditedBy -> textFirstEditedBy, upstream's own down migration;
draw/highlight sequence clamp when no segment uses the new `dim`
encoding) and throws on anything else from the future. On a networked
machine the right move is upgrading every tldraw package to one
matching current version in a single commit; the pre-step then becomes
dead code that can go.

Protocol compatibility: server and clients must run the same pinned
version; both come from the same lockfile, so that is automatic. The
room's clock is in-memory, so a sync-server restart is a new epoch and
clients resync silently.

## Ownership

`meta.owner` on every page and shape, stamped by migration for
existing content and by `getInitialMetaForShape` for new shapes. Pure
rules in `web/src/calculations/canvasOwnership.ts` (presenter owns
structure and anything unowned; an attendee owns their workspace shape
and drawings; pages and the document record are presenter-only; assets
upload for all, delete presenter-only). Enforcement is in every
client via store side effects (`registerCanvasPermissions`): blocked
change returns prev, blocked delete returns false, disallowed create
is removed in-transaction, and only for `source === "user"` so remote
records from the authoritative server stream are never fought.
Server-side, sessions without a joined userId or the presenter flag
are read-only at the socket. No auth exists; a hand-rolled client can
bypass per-shape rules, and the docs say so plainly.

## Presenter target

`presenter_state` gained `revision` (monotonic, bumped inside the
UPDATE statement), `target_frame_id`, `target_bounds_json`. The design
is camera-bounds-first with the frame id riding along: bounds always
exist, the frame adds degradation semantics. Resolution is pure
(`calculations/presenterTarget.ts`): live frame bounds (inset 48),
else captured bounds, else page fit plus a concise notice, else stay
put with a notice when the page itself is gone. Clients order on
revision alone; the first poll applies the current driven state (late
joiners), afterwards only strictly newer revisions apply, single
flight. Bring-everyone captures the presenter's viewport; Prev/Next
broadcasts the frame while presenter mode is active; the presenter's
own camera is never driven.

## Deck network path

- `deck/vite.config.ts` (merged by Slidev): LAN binding plus `/api`
  proxy to the backend. LiveRoom's default apiBase is now `/api`.
- LiveRoom's connection handling is a pure four-phase state machine
  (`deck/lib/liveRoom.ts`: connecting, connected, recovering with
  stale data visible, unavailable), tested in `deck/tests/`.
- The deck panel rewrites a localhost deck URL to the app's hostname
  at render time (`web/src/calculations/deckUrl.ts`); the stored shape
  prop is untouched.
- Backend CORS lists the four documented localhost dev origins only.
  LAN traffic rides the proxies, which are server-to-server.

## Canvas migrations

`web/src/calculations/canvasMigrations.ts`, version in the document
record's meta, currently 4: ensure-workshop-pages (seeds starter
content only for pages the migration itself creates),
ensure-modality-panels (the actual bug fix: panels appear on non-empty
pages), ensure-deck-panel, stamp-ownership. Idempotent, input never
mutated, unknown shape types untouched, failure aborts the room load.
Record builders emit complete 5.1.1 records (no Editor exists
server-side to fill defaults); tests validate every built record
through the real tldraw validators and push the repository's actual
authored snapshot through migration plus tldraw's own migrator, twice.

## Tests run

- `just lint`, `just typecheck`, `just test`: all clean (api 265,
  web 184, deck 6).
- `just test-e2e`: 8 passed. room.spec.ts covers acceptance cases 1-4
  with real browser contexts (concurrent edits + reloads, protection
  of authored structure and other attendees' shapes, presenter
  bring/Next following for an existing attendee and a late joiner,
  send-to-workspace release), plus panel-overlap checks at 1920x1080
  and 1280x800. Acceptance case 5 (LiveRoom) is unit-tested at the
  state machine and was exercised live through the Slidev proxy (502
  with backend down, real payload with it up). Acceptance case 6
  (old snapshot migrates once, stable on second load) is covered by
  the migration suite against the real authored snapshot; the e2e
  stack additionally boots a fresh canvas through the migration path
  on every run.
- Manual multi-client evidence: the Playwright multi-context runs are
  the reproducible form of it; the sync server's health endpoint was
  also watched during live boots (sessions count, persist status).

## Capacity

The room fans out every change to every session over one Bun process;
40 attendees drawing simultaneously is well inside what the engine is
built for (tldraw's own hosted rooms are larger). The load test tool
(`just load-test`) still exercises only the HTTP API, not WebSocket
fan-out; if that worries you, a rehearsal with a handful of real
browsers is the honest check. Nothing in this phase changed backend
throughput characteristics.

## Review findings addressed after the first pass

Ramon's review surfaced nine findings; all are fixed on this branch.

1. Durability is now visible separately from liveness: the app polls
   the sync server's health endpoint and shows Canvas: saving / saved /
   save failed (retrying) next to the room state. "Room: live" no
   longer hides a dying backend.
2. flush() reports whether dirty state remains (Promise<boolean>). The
   sync server's shutdown retries three times and exits nonzero with a
   loud message when unsaved changes remain; boot refuses to open the
   room if the initial migrated persist fails.
3. A presenter revision is consumed only after the view successfully
   applied. A transient failure (the send-to-workspace workspace
   lookup) retries the same revision on the next poll instead of
   stranding the attendee, and no longer produces an unhandled
   rejection.
4. The join effect navigates to the workspace only when a successful
   presenter-state response confirms a non-presenter mode; an
   unreachable backend is no longer read as permission to move the
   camera.
5. Workshop versions above the runtime's are rejected before the room
   opens, and the boot persist triggers on `changed` (including
   schema-only down-conversions), not just on named migrations.
6. Unknown record and shape types now fail the load loudly with the
   disk snapshot untouched, instead of being passed through to
   validators and clients that cannot represent them. The
   "preservation" test now uses the registered legacy notebook panel;
   the unknown-type, forward-version, and downgrade-only cases have
   their own tests. This supersedes the earlier claim that unknown
   types pass through.
7. LiveRoom polls resolve latest-wins through a token gate; a slow old
   response can no longer overwrite fresher data or the recovery
   state.
8. A failed slide broadcast surfaces "Slide broadcast failed. Attendees
   did not follow." through the notice area instead of being swallowed.
9. `just start` uses `wait -n`: the first service to exit takes the
   stack down instead of leaving a half-alive room. The complete
   release command surface remains phase 36's item.

## Second review round

Four more findings, all fixed.

1. The migration gate now actually gates. Unknown schema sequences are
   rejected in the pre-step (previously skipped silently), and before
   the room opens, every migrated record runs through tldraw's own
   migrator plus the real validators (upgradeAndValidateDocument in
   sync-server/schema.ts). A malformed note with empty props was
   reproduced refusing the boot with exit 1 and a byte-identical disk
   snapshot. The boot persist also triggers when tldraw's up-migration
   changed anything, not only when workshop steps ran. Tests cover the
   unknown sequence at version 99, the malformed known record, and the
   valid document passing the gate.
2. LiveRoom polling is single-flight with an 8s abort timeout instead
   of latest-wins tokens: a request slower than the 3s interval lands
   instead of being discarded by newer tokens (the starvation case),
   and a hung request cannot block the loop. The poll logic moved into
   deck/lib/liveRoom.ts (pollRoomOnce, createSingleFlight) and is
   tested with delayed and hanging fetches.
3. Join navigation retries until presenter mode is actually known
   (actions/joinNavigation.ts). The retry is unbounded by design: the
   presenter poll cannot stand in for this decision because its first
   successful read of an idle room applies nothing, so any fixed
   budget would strand an attendee after a long enough outage. The
   loop ends only with an answer or with the abort of the effect that
   started it (a bounded budget exists for tests). Each attempt runs
   under its own request timeout (default 4s) and is wired to the
   caller's AbortSignal, so a stalled request neither freezes the loop
   nor outlives the App effect. Tested for the 500-then-idle path,
   confirmed presenter mode, a twelve-failure outage resolving on
   recovery, a hang cut off by the request timeout, a hang ended by
   the caller's abort, and an already-aborted signal.
4. Durable recovery is demonstrated end to end in
   e2e/durability.spec.ts, its own Playwright project: it boots a
   complete stack on OS-allocated ports (net.listen(0) per service,
   scratch state in a mkdtemp directory) held as exact child process
   handles in their own process groups, so two worktrees can run the
   spec at once without claiming each other's services. Readiness
   belongs to the spawned child: waitForReady throws when the child
   exits (say, after losing a port race) instead of accepting a 200
   from a foreign responder. Restarts signal the
   owned PID group and wait for exit before the replacement binds; no
   pkill patterns exist, so other worktrees and the shared webServer
   stack are untouchable by construction. The flow: an edit is read
   back from GET /canvas, the sync server restarts and a fresh room
   serves the edit after a reload, stopping the backend surfaces the
   visible "save failed, retrying" badge while the room stays live,
   and the restarted backend drains the retry loop back to "saved"
   with the offline-era edit on disk. The Vite proxy targets follow
   CHESS_STUDIO_API_PORT / CHESS_STUDIO_SYNC_PORT (defaults 8000 and
   8010) so the isolated dev server matches.

## Known issues / tech debt

- `TLSocketRoom`'s `initialSnapshot` and `onDataChange` options are
  deprecated upstream in favor of the storage API; they work at 5.1.1
  and keep the code small. Revisit when the stack is upgraded.
- The permission side effects run client-side only. Fine for the
  room's threat model, but worth restating in any future multi-room
  or public deployment discussion.
- `window.chessStudioEditor` is a deliberate e2e/debug hook set in
  App; if someone objects, it can be gated behind import.meta.env.DEV.
- The legacy `NotebookShapeUtil` remains for old snapshots and is
  untouched, per the phase constraints. The notebook is not a canvas
  requirement.
- `just reset-canvas` requires the stack stopped (the room would
  persist the in-memory document right back). Documented in
  local-dev.md and demo-plan.md.

## What the next phase should tackle first

Phase 33 is truthful evaluation; nothing here blocks it. If any spare
time exists, the two worthwhile follow-ups from this phase are a
real-browser soak with ~10 clients on the venue laptop and the tldraw
stack upgrade on a networked machine (drop the down-convert pre-step
afterwards).

## Gotchas

One race found by the e2e suite and fixed in App's join effect: a
late joiner during an active presentation used to be pulled to the
presenter's view by the first poll and then yanked back to their own
workspace when the join flow's navigateToWorkspace resolved, after
which the already-consumed revision never re-applied. The join effect
now checks presenter state and skips its camera move while mode is
"presenter". If remote navigation ever looks flaky again, start there.


- bun.lock was edited by hand (offline environment, no registry).
  `bun install` accepted and normalized it; if you touch dependencies
  on a networked machine, just use bun's own resolver.
- Bun's cwd for `bun install` follows the nearest package.json; run it
  inside web/ or deck/ explicitly.
- The sync server must be restarted after `just reset-canvas` or a
  snapshot restore; it holds the document in memory.
- Slidev merges `deck/vite.config.ts` silently. If the proxy ever
  stops working, check Slidev's config merging first.
- Playwright's first webServer boot can race the backend; the sync
  server retries GET /canvas for 30s, which is what makes parallel
  webServer startup safe.
- e2e state accumulates within a run (one shared room, one scratch
  DB): tests that need a specific camera position navigate explicitly
  rather than assuming a fresh viewport.
