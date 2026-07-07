# Handover: phase 29, the room dashboard and proving 40 attendees fit

Written 2026-07-07, from Ramon's three questions: can I watch all
games and collect the data in one click, is the LLM path async, and
can we simulate 40 attendees.

## What was built

**Presenter games dashboard.** GET /presenter/games returns every
game in the room (active first) with the player's name, per-game
legal move and dataset-row counts, seconds_left for running clocks,
and room totals. The action (`room_games`) reconciles every active
clock with the wall clock first, so abandoned games show as the
timeout losses they are. The presenter panel grew a Games section:
totals line ("12 playing, 3 finished, 4092 samples"), a scrollable
list with live countdowns and results, polled every 3 seconds.

**One-click collection.** Two buttons under the dashboard:
- Download SFT dataset: the existing chess_sft.jsonl export
  (prompt/completion pairs, what the snippets load).
- Download all shapes: new POST /datasets/text/export-full writes
  chess_all_shapes.jsonl, every dataset row from every workspace
  across all six shapes, each line carrying shape + workspace_id +
  created_at alongside the payload. The instructor's take-to-the-GPU
  file. Both gitignored (and the WAL sidecar files too, see below).

**Concurrency hardening.** Three changes, each answering "is it
async?" in practice:
- SQLite now runs `journal_mode=WAL`, `busy_timeout=10000`,
  `synchronous=NORMAL`, connect timeout 10s. Readers stop blocking on
  writers, and colliding writers queue instead of throwing "database
  is locked". Side effect: the backend test suite dropped from ~20s
  to ~5s because commits got cheap.
- The anyio sync-route thread pool is raised from 40 to 120 in the
  lifespan. Every sync route holds a worker thread, and model-move /
  assess hold theirs for the entire upstream LLM round trip; 40
  attendees with two LLM-bound calls per exchange would saturate the
  default pool.
- `get_or_create_presenter_state` uses INSERT OR IGNORE: the load
  test's join burst exposed a check-then-insert race on the singleton
  row (two 500s out of 300 requests at cold start). Exactly one
  insert wins now.

**Load test tooling** (`tools/`, run via Justfile):
- `just mock-llm [delay]`: an OpenAI-shaped ThreadingHTTPServer that
  answers move prompts with the first legal move and everything else
  with a canned assessment, sleeping `delay` seconds per reply.
  Threaded matters: a single-threaded mock serializes the entire
  room and you end up load testing the mock.
- `just load-test [attendees] [duration]`: asyncio + httpx simulator.
  Each attendee joins, starts a timed match, plays random legal moves
  with think time, triggers model-move and assess per exchange (the
  UI does), and polls /presenter every 3s. One extra client polls the
  dashboard. Prints per-endpoint p50/p95/p99/max and error counts.

**Measured, on a 4-core 15GB container** (Ramon's laptop is 20-core
32GB, so these are a floor), mock delay 1.2s:
- 20 attendees / 45s: 320 moves, all endpoints error free after the
  singleton fix. Moves p50 6ms.
- 40 attendees / 60s: 682 moves recorded (10.2/s), 1963 requests,
  zero 5xx, zero tracebacks. Moves p50 21ms p99 407ms; model-move and
  assess p50 ~2.1s (1.2s mock latency + ~0.9s queueing); presenter
  poll p50 23ms; the dashboard endpoint p95 ~2.1s under full blast
  (acceptable: it is one presenter polling it).
- 4092 dataset rows accumulated in 60s of simulated play; the full
  export returned all 4092 and the dashboard rendered 40 live
  countdowns.

## Answers to Ramon's questions, for the record

1. Dashboard + one-click download: built, above.
2. Async: the LLM client is sync httpx inside sync routes; FastAPI
   runs those in a thread pool, so the event loop never blocks, but
   each in-flight LLM call costs a thread. With the pool at 120 and
   the measured profile, 40 attendees fit with roughly 3x headroom.
   A true async rewrite of llm_client remains unnecessary until the
   room triples.
3. Simulation: `just load-test`, repeatable anywhere, numbers above.

## Intentionally deferred, and why

- **Async llm_client.** The threadpool answer holds to ~100+
  concurrent LLM-bound requests. Not worth the rewrite risk before a
  workshop.
- **Dashboard pagination/virtualization.** 40 rows in a scrollable
  list is fine.
- **Auth on the presenter endpoints.** Same standing posture as
  ?presenter=1: LAN convenience, not security.
- **The sim does not exercise canvas saves.** Attendees rarely edit
  the shared canvas; moves, matches, and polling are the real load.

## Known issues / tech debt

- The load sim leaves its users/games in whatever DB the backend
  points at. Run it against a scratch CHESS_STUDIO_DB_PATH (the docs
  say so), or `just reset-db` after.
- window.open for the downloads can be blocked by popup blockers if
  the browser is feeling moody; the click is a direct user gesture so
  default settings allow it.
- The dashboard endpoint recomputes per-game counts with correlated
  subqueries on every poll. At 40 games that is nothing; at 400 it
  would want an index or a cached rollup.

## What the next phase should tackle first

1. Still: one real run against api.openai.com. The load test now
   exists precisely so the rehearsal can compare real-latency numbers
   against the mock baseline (`just mock-llm 2.5` approximates a slow
   day).
2. Run `just load-test 40` on the actual workshop laptop and eyeball
   the report.

## Gotchas

- WAL mode creates euro_chess_studio.db-wal / -shm sidecars next to
  the DB; both gitignored now. Deleting the .db without its sidecars
  mid-run is how you corrupt a database; `just reset-db` handles it.
- The threadpool limiter must be set inside the lifespan (needs a
  running event loop), not at import time.
- The mock LLM must stay ThreadingHTTPServer. The scratchpad version
  used HTTPServer and would have serialized the whole room's model
  calls behind one socket.
- pydantic's extra="ignore" is doing quiet work in RoomGameOut:
  `**dict(row)` passes created_at and friends, which are dropped.
  Add a field to the model and it starts flowing, no other change.
