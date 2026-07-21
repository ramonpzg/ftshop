# Handover: phone TUI demo

Written 2026-07-21 on branch `claude/phone-tui-demo-obvg5e` (the phase
doc names `demo-termux-chess-tui`, which an experimental attempt
elsewhere occupies; Ramon asked for a unique branch name). Base was
accepted `main` after phase 35. The deliverable is `tui/`, a
self-contained phone-first chess TUI, plus `docs/phone-tui.md`, the
Justfile wiring, and the acceptance evidence below.

## Sources consulted, 2026-07-21

- llama.cpp `tools/server/README.md` (master): `llama-server` binary,
  `POST /v1/chat/completions`, `/health`, `/v1/models`,
  `--reasoning [on|off|auto]`, `--reasoning-format`, `response_format`
  with `json_object` and `json_schema`, `-hf`, `--alias`,
  `--no-mmproj`, chat template from GGUF metadata.
- llama.cpp `docs/android.md`: Termux via `apt install git cmake
  libandroid-spawn` and a standard CMake build; keep `-c` modest
  (about 4096) or memory spikes can kill the terminal.
- llama.cpp release page: current tag b10075, 2026-07-20. The build
  used for acceptance is source commit `76f46ad` (same date).
- Gemma 4 core and prompt-formatting docs: real system role, thinking
  controlled by a `<|think|>` system token, `<|channel>thought`
  blocks; all owned by the chat template. The TUI sends plain
  messages, never Gemma control tokens, exactly as the phase requires.
- `google/gemma-4-E2B-it-qat-q4_0-gguf` model card: files
  `gemma-4-E2B_q4_0-it.gguf` (3.35 GB) and
  `gemma-4-E2B-it-mmproj.gguf`; 2.3B effective parameters, 128K
  context, QAT; recommended `llama serve -hf ...:Q4_0`; unquantized
  twin `google/gemma-4-E2B-it-qat-q4_0-unquantized`. Repo is not
  gated.
- llama-cpp-python README: compiled at install; on phones "Docker on
  termux (requires root) is currently the only known way". Not used.
- uv on Termux: no package, aarch64-linux-android build failures
  (astral-sh/uv#2705, termux/termux-packages#21096). Phone installs
  use pip in a venv; uv stays the desktop path. `uv sync --project
  tui` works on desktops and is what the Justfile uses.
- Textual on Termux: install failures via tree-sitter extras
  (Textualize/textual#5644) plus slow phone cold-start reports. With
  no phone available to smoke-test, the UI is Rich plus a frame/input
  loop. One UI implementation, as required.

## What was built

`tui/` is its own uv project (pyproject, uv.lock, hatchling, ruff, ty,
pytest) with runtime deps python-chess, httpx, rich, all pure Python.
The phone never resolves FastAPI, Jupyter, torch, audio, web, or deck
dependencies.

Boundaries follow the repo rule:

- `calculations/`: `board_view` (cell grid plus exact 22-column text
  contract), `moves` (UCI/SAN participant parsing, promotion, phone
  auto-capitalization tolerance, numbered SAN history, sorted legal
  list), `prompt` (versioned system prompt `tui-move-v1`, user and
  corrective messages, the JSON schema), `replies` (fence-tolerant
  extraction copied from the backend's proven `extract_json_object`,
  shape and legal-set judgment), `commands`, `stats`.
- `data/`: `config` (env plus flags, base URL normalized once, XDG db
  path, api_key excluded from repr), `db` (schema), three repos
  (games, plies, model_attempts; no commits in repos), `llm_client`
  (the one httpx boundary; OpenAI-style nested json_schema
  response_format, stream false, temperature 0.3, max_tokens 192,
  bounded error excerpts, injectable transport).
- `actions/`: `game` (start, participant move committed before any
  network call, the model turn state machine with one corrective
  request, per-attempt persistence committed as evidence lands,
  outcome finalization via `board.outcome()`), `replay` (history,
  cursor).
- `ui/`: `theme` (chalk palette lifted from `deck/style.css`
  `style-chalk` tokens; PLAIN theme styles nothing), `screens` (all
  rendering; styled board walks the same grid as the text contract),
  `app` (the loop, screen dispatch, spinner while the model thinks,
  central notice rendering).

Failure policy implemented exactly as specified: malformed or illegal
reply gets one corrective request containing the rejected reply, the
exact reason, and the unchanged legal list; a second failure shows
"Gemma did not return a legal move. retry or quit" with the reason
underneath and the board untouched. Transport failure, timeout, and
HTTP error are separate visible states with the same retry recovery.
No fallback move exists anywhere. Ctrl+C during a model call records a
canceled attempt and returns to the retry state instead of killing the
app; Ctrl+C or Ctrl+D at a prompt exits.

Persistence: games, plies (FEN before/after, SAN, capture flag,
comment), model_attempts (attempt number continuing across retries,
corrective flag, status, raw reply, parsed move, request id, latency,
error detail). The record aggregates W/L/D, completed games, and
captures by the participant in won games (the secondary personal
objective). Unfinished games stay unfinished and out of the record.
Replay reproduces stored positions and comments; nothing labels
mistakes because nothing evaluates moves.

Justfile: `phone-tui`, `test-tui`, `package-tui`; `install`, `test`,
`lint`, `typecheck`, `format` now cover `tui/`. CLAUDE.md layout and
README command table updated.

## Checks run

- `tui`: 124 pytest tests, ruff clean, `ty check src` clean,
  `uv build` produces sdist and wheel.
- Full surfaces: api 471 passed, web 263, deck 174, tui 124;
  `just lint` and `just typecheck` clean across all four projects.
- Board rendering matches the phase prompt's reference block byte for
  byte and is pinned at widths 40/48/60/80 in both chalk and plain
  themes; a db-byte scan proves no API key, `Bearer`, or
  `Authorization` string ever lands on disk.

## Live acceptance against real llama.cpp and the exact Gemma

Environment: this container (x86_64 Linux, 4 cores), llama.cpp built
from source at commit `76f46ad` (2026-07-20, release b10075 era,
CPU only, GNU 13.3), and the exact deployment GGUF
`gemma-4-E2B_q4_0-it.gguf` (3,349,516,256 bytes) downloaded from the
model card repo, which is not gated. Server command as documented:
`llama-server -m ... --alias gemma-4-2b-local --host 127.0.0.1
--port 8080 --no-mmproj --reasoning off -c 4096 -t 4`. Flags verified
against the binary's own help: `--reasoning [on|off|auto]`,
`--no-mmproj`, `--alias` all current. `/health` and `/v1/models`
answer as documented; the alias comes back as `gemma-4-2b-local`.

### The one real defect the live run found, and its fix

With the first schema (move constrained by the UCI regex pattern),
the live model failed twelve consecutive attempts across six turns,
every reply `illegal`, every raw reply persisted. The ledger shows
the mechanism: Gemma anchored on the SAN column of LEGAL_MOVES and
wanted to answer "e5"; grammar decoding then forced two more square
characters and emitted pattern-valid junk, `e5b5` and `e5e6`,
regardless of the corrective request:

```text
a1 illegal: {"move":"e5b5","comment":"A standard, if slightly slow, opening. Proceed."}
a2 illegal: {"move":"e5e6","comment":"Solidifying the center, predictable."}
... ten more of the same shape
```

Fix: `move_json_schema(legal_uci)` constrains `move` to an enum of
the turn's actual legal UCI list (verified accepted by this build,
three for three legal e7e5 at ~2.4s warm). The model's probability
mass flows to the listed spelling instead of being padded into junk.
The application still validates shape and membership on every reply;
against a server that ignores `response_format`, the corrective and
retry machinery still carries the turn, and the MockTransport tests
keep that path pinned. `MOVE_PROMPT_VERSION` bumped to `tui-move-v2`;
the system prompt text itself is unchanged.

### Green acceptance run (after the fix)

- Three model turns in one game: 1. e4 e5 2. Nf3 d5 3. Bc4 dxc4, all
  applied on the first attempt, latencies 5.6s, 10.5s, 8.1s, with
  in-character comments ("White's center is a nuisance, but we meet
  it with a pawn."). dxc4 is a real capture recorded with its flag.
- Restart (new connection, new App): history lists the game, replay
  reproduces all six stored positions against a python-chess replay,
  comments intact after reload.
- Attempt ledger for the green game: three rows, all `applied`,
  latencies persisted; db byte scan shows no `Bearer` or
  `Authorization` anywhere.
- Server death mid-turn: with the server killed, the turn fails in
  0.0s as `unreachable`, White's move stays applied, black to move,
  typed moves are refused with "waiting on Gemma. retry or quit".
  A retry during the restarted server's model load records the
  distinct `HTTP 503 Loading model` state. After `/health` goes ok,
  `retry` repeats the same turn and lands (8.7s). Ledger:
  transport_failed, transport_failed(503), applied, attempts 1-3.
- The real binary end to end: `printf "new\ne2e4\nquit\nquit\n" |
  chess-tui` against the live server plays the opening, shows the
  comment, and exits through the home record screen.
- Timings: app cold start to first frame 0.30s median (uv wrapper
  included; bare interpreter 0.03s); model load 2.9 to 9.4s with the
  GGUF in page cache; a full move turn 2.4 to 10.5s. Phone magnitudes
  will differ; the recording starts after the server is warm.

### Not validated

Real Termux on the target phone. This environment has no Android
device. docs/phone-tui.md states this plainly and gives the exact
one-line smoke command to run in Termux before trusting the setup.
Desktop Linux results above are not reported as Android validation.

## Intentionally deferred

- Resignation and draw offers: not in the command set the phase fixed;
  quitting mid-game leaves an honest unfinished game instead.
- Unicode piece glyphs: single-cell width on the target phone is
  unverifiable from here, and ASCII letters are the monochrome-safe
  invariant anyway. If wanted later, add a flag only after a real
  Termux width check.
- Arrow-key replay: optional per the phase; `next`/`prev`/enter work
  everywhere including Termux's extra-keys row.
- Streaming replies: `stream: false` per the phase; the spinner covers
  perceived latency and a chess move is one short JSON object.
- No resume of an interrupted game: replay is the recovery story; the
  recording never needs mid-game resume.

## Known issues / tech debt

- The corrective request doubles the prompt (rejection preamble plus
  the original message). Fine at chess sizes; do not reuse the pattern
  for long-document tasks without bounding.
- `list_games_newest_first` orders by `started_at` then rowid;
  timestamps are second-precision ISO, so ordering inside one second
  is insertion order, which is correct locally but would need a
  tiebreak rethink if games ever merged across devices.
- The app clears the screen per frame; scrollback in the same tab is
  sacrificed deliberately (one screen at a time). Termux users who
  want logs should use the server tab.
- `console.status` spinners only run on a real tty; piped/CI runs
  print the waiting line once instead. Cosmetic by design.

## What the next phase should tackle first

Nothing in this package blocks the release phases. If phase 36 wants
the TUI in preflight, add `just test-tui` to the preflight list and
consider a `chess-tui --check` subcommand that hits `/health` and
`/v1/models` and reports the alias, so the recording setup can be
verified in one line.

## Gotchas

- httpx base-URL joining is deliberately not used: the client builds
  `{base_url}/chat/completions` as a plain string, so there is no
  ambiguity about `/v1` being kept. Normalize the trailing slash in
  config, nowhere else.
- `judge_move_reply` lowercases and strips the move before matching,
  so a legal set must be lowercase UCI (it is, python-chess emits
  lowercase). Do not pass SAN into the legal set.
- python-chess raises `AmbiguousMoveError`/`IllegalMoveError` as
  subclasses of `ValueError`; catch order in `parse_participant_move`
  matters. The generic `ValueError` arm must stay last.
- Rich `Console(record=True)` styling: `export_text()` strips ANSI, so
  geometry tests compare visible text; `export_svg(theme=...)` is
  where the chalk terminal palette applies. `color_system="truecolor"`
  must be forced for faithful SVG capture.
- `datetime.now(UTC).isoformat(timespec="seconds")` is the one
  timestamp format; history slices `[:16]` for display and assumes it.
- The fivefold-repetition game ends on the model's reply mid-loop;
  any scripted test that shuffles knights must check `state.over`
  after every ply, not per cycle.
- sqlite `executescript` commits implicitly; `db.connect` is the only
  place that touches schema and the explicit commit after it is
  deliberate noise so nobody wonders.
- Grammar-constrained decoding warps intent when the constraint
  permits strings the model wants to start but cannot finish legally.
  A pattern that admits "e5??" invites SAN-anchored junk; an enum of
  full legal strings steers the same intent to a valid completion.
  If a future task constrains model output with llama.cpp grammars,
  prefer enumerating the real action space over shaping it.
- llama.cpp answers requests during model load with HTTP 503
  "Loading model" while the socket is already accepting. A health
  poll that only sleeps on connection errors will spin through its
  budget in milliseconds once the socket opens and report ready too
  early. Poll `/health` for 200 and sleep on every iteration.
- The phase-33 warning about pkill holds and extends to
  `pgrep -f`: the pattern matches the killing shell's own command
  line, and killing it took the foreground script's process group
  down too. Kill by exact name (`pgrep -x llama-server`) or by pid.

## Files

- `tui/pyproject.toml`, `tui/uv.lock`
- `tui/src/chess_tui/` (18 modules plus package inits, per the
  boundary list above)
- `tui/tests/` (conftest plus 13 test files, 124 tests)
- `tui/screenshots/` (9 SVG plus text frame captures)
- `docs/phone-tui.md` (runbook, config, troubleshooting, shot list)
- `notes/ai/phone-tui-demo.md`, `notes/hu/phone-tui-demo.md`
- Justfile, CLAUDE.md, README.md, .gitignore touched for wiring
