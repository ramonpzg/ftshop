# Phone chess TUI

A terminal chess app for the workshop opening recording. It runs on an
Android phone inside Termux, talks to a llama.cpp server on the same
phone over the OpenAI-compatible Chat Completions API, and plays you
against Gemma 4. A coin toss decides who gets White. One screen at a
time inside the terminal's alternate screen buffer, typed moves and
slash commands with live suggestions, a persistent named record, and
replay.

The code lives in `tui/`, a self-contained uv project. It never
imports the workshop backend and keeps working if the whiteboard stack
is absent.

## Runtime facts, checked 2026-07-21

- llama.cpp server docs (tools/server/README.md) confirm
  `POST /v1/chat/completions`, `GET /health`, `GET /v1/models`,
  `--reasoning off`, and model chat templates from GGUF metadata.
  Verified live against a source build of commit `76f46ad`
  (2026-07-20, release b10075 era).
- The move constraint rides as llama.cpp's raw GBNF `grammar` field,
  not `response_format: json_schema`. Both were verified working on
  the desktop build, but grammar support predates json_schema by
  years, and Ramon's Termux build demonstrated the difference on
  day one: it ignored `response_format`, free-ran every reply to the
  full 192-token cap (12s of generation), and returned an unlisted
  move. The GBNF grammar enumerates the turn's actual legal UCI moves
  inside the fixed JSON shape, so a conforming server can only emit a
  listed move and generation stops at the closing brace, roughly 35
  tokens. The application still validates shape and legal-set
  membership on every reply; against a server that ignores `grammar`
  too, the corrective request and retry states carry the turn.
- Earlier drafts constrained the move with a UCI regex pattern
  instead of the legal menu. Live Gemma 4 E2B anchored on the SAN
  column, wanted "e5", and grammar decoding padded it into
  pattern-valid junk ("e5b5") twelve attempts straight. Enumerating
  the menu redirects the same intent to the listed spelling; since
  the change every live turn has applied on the first attempt.
- Gemma 4 has a real system role and thinking control tokens; the
  server owns both through the chat template and `--reasoning off`.
  The TUI sends plain messages and never writes Gemma control tokens.
- The deployment model is `google/gemma-4-E2B-it-qat-q4_0-gguf`
  (file `gemma-4-E2B_q4_0-it.gguf`, 3.35 GB, QAT Q4_0, 2.3B effective
  parameters). The repo also ships `gemma-4-E2B-it-mmproj.gguf`; this
  text-only game never loads it (`--no-mmproj`).
- llama-cpp-python is not used. Its own README says Docker on rooted
  Termux is "currently the only known way to run this on phones".
  The native server plus HTTP wins, and no `outlines`-style package
  is needed: GBNF over HTTP is the same constrained decoding without
  a second inference stack.
- uv works on Ramon's Termux in `uv venv` plus `uv pip install`
  mode against the Termux CPython (validated on the phone,
  2026-07-21). `uv sync` with managed Pythons is still not a Termux
  path (astral-sh/uv#2705, termux/termux-packages#21096). Plain pip
  in a venv remains the fallback that always works.
- The UI is Rich plus a frame-render input loop inside the alternate
  screen buffer, not Textual. Textual has documented Termux install
  failures through its tree-sitter extras (Textualize/textual#5644)
  and slow phone cold starts. Plain ANSI plus blocking `input()` has
  no terminal-capability dependencies beyond color, which degrades
  cleanly. One UI implementation only.

## Termux setup

Prerequisites on the phone: Termux, llama.cpp built or installed and
working, Python 3.11+.

```bash
pkg update
pkg install git python
git clone <this repo>
cd <repo>
uv venv .venv && source .venv/bin/activate && uv pip install ./tui
```

No uv on the phone? Same thing with stock tools:

```bash
python -m venv .venv && source .venv/bin/activate && pip install ./tui
```

Everything the TUI needs is pure Python (python-chess, httpx, rich);
nothing compiles. On a desktop: `uv sync --project tui` then
`just phone-tui`.

## Start the server, then the TUI

Termux tab 1, the model server. Modeled on the command already proven
on Ramon's phone, moved to port 9017 because half the world squats on
8080:

```bash
llama-server \
  -hf google/gemma-4-E2B-it-qat-q4_0-gguf:Q4_0 \
  --offline \
  --no-mmproj \
  --reasoning off \
  -c 8192 -ctk q8_0 -ctv q8_0 \
  --host 127.0.0.1 \
  --port 9017 \
  --alias gemma-4-2b-local
```

Drop `--offline` for the first run so the GGUF can download. The
quantized KV cache (`-ctk/-ctv q8_0`) and `-c 8192` are phone-sized;
anything at or above `-c 4096` is plenty for chess. Keep the alias
matched to the TUI's model name so recorded provenance stays honest;
llama.cpp would serve a mismatched name anyway, silently. Wait until
`curl -s http://127.0.0.1:9017/health` says `{"status":"ok"}`.

Termux tab 2, the game:

```bash
source .venv/bin/activate
chess-tui
```

First launch asks your name once and remembers it; `--name` or
`CHESS_TUI_NAME` override it. Games recorded before names existed are
claimed by the first name given.

## Playing

`/new` starts a game and a coin toss assigns colors. If Gemma gets
White it opens immediately; the board always sits with your side at
the bottom, and `/flip` turns it around. The status line reads
`ramon: Black | Gemma: White | move 2`.

Commands are slash words; the bare words work too. The moment you
type `/`, the matching commands appear on a line under the input and
narrow as you keep typing; tab completes the rest (`/ret` tab gives
`/retry`). Suggestions need a real terminal; piped input falls back
to plain reads. No function keys, no mouse:

```text
/new      start a game. a coin toss picks your color
/back     return to the game or previous screen
/history  past games, newest first, with your color per game
/replay   step through a stored game. enter advances
/retry    repeat a failed model turn
/flip     turn the board around
/help     the command list
/quit     leave the screen. at home, exit
```

Moves are typed as UCI (`e2e4`) or SAN (`e4`, `Nf3`, `exd5`, `O-O`,
promotion `e7e8q` or `e8=Q`). An active game survives `/help`,
`/history`, `/replay`, and even `/quit` to the home screen; the home
screen shows `game in progress. /back returns to it`.

While Gemma thinks the screen says `Gemma is choosing...`. A reply
that fails validation gets exactly one corrective request naming the
rejection; if that also fails you see

```text
Gemma did not return a legal move. retry or quit
```

with the reason underneath and the board unchanged. A dead server,
a timeout, and an HTTP error are separate visible states with the
same recovery. No fallback move is ever attributed to Gemma.

## Configuration

Defaults suit the phone. Environment variables, with equal CLI flags:

```text
CHESS_TUI_BASE_URL=http://127.0.0.1:9017/v1   --base-url
CHESS_TUI_MODEL=gemma-4-2b-local              --model
CHESS_TUI_API_KEY=local                       --api-key
CHESS_TUI_TIMEOUT=120                         --timeout
CHESS_TUI_DB=<path>                           --db
CHESS_TUI_NAME=<name>                         --name
NO_COLOR=1                                    --no-color
```

The API key is sent as a bearer header and nowhere else: never stored,
never displayed, absent from the SQLite file (tested by scanning the
db bytes). The local server does not need a real credential.

Games live in SQLite under the XDG data directory,
`~/.local/share/chess-tui/games.db`. The schema migrates in place;
games from the first build survive and count. Every ply stores FEN
before and after, every model reply is kept raw with request id and
latency, and replay renders exactly what was stored, your color in
the header. Model comments are model commentary, not engine analysis;
nothing is ever labelled a mistake because nothing evaluates moves.

## Measured shape of a turn

From Ramon's phone (llama.cpp local build, Gemma 4 E2B Q4_0): prompt
processing about 112 tokens/s, generation about 15.7 tokens/s. A move
turn sends roughly 540 prompt tokens and, grammar-bounded, generates
about 35, so a warm turn lands around 6 to 8 seconds; without the
grammar honored the same turn free-ran to 192 tokens and took 17.
Desktop acceptance (4-thread x86 CPU): turns 6.8 to 12.5 seconds,
model load 3 to 9 seconds warm, app cold start 0.3 seconds. Start
recording after `/health` is ok and one warm-up move played off
camera.

## Troubleshooting

- "server unreachable. retry or quit": the server tab died. Check
  `curl -s http://127.0.0.1:9017/health`, then `/retry`.
- "server error. retry or quit" with `HTTP 503 Loading model`: the
  server is up but still loading the GGUF. Wait for health, `/retry`.
- "Gemma timed out. retry or quit": thermal throttling or a cold
  cache. Raise `--timeout`, keep the server warm, `/retry`.
- Gemma played instantly with a strange move on an old build: check
  the server honors `grammar` (any llama.cpp from recent years does).
  The TUI's corrective flow covers the rest and the attempt ledger in
  the db shows exactly what came back.
- Narrow terminal: the board is 37 columns wide with four-character
  cells, and on terminals 27 rows or taller each rank gets a second
  background row, which makes the squares square. Under 27 rows the
  board drops to single-height automatically; under 40 columns lines
  crop rather than wrap, so shrink the Termux font one step.
- Scrollback shows old frames: only outside the alternate screen.
  The app enters it on start and restores your shell on exit; if it
  ever crashes hard, `tput rmcup` or `reset` brings the terminal
  back.
- Colors look flat: NO_COLOR or the terminal stripped them. Case
  carries the piece distinction; the game is fully playable plain.

## Recording shot list, 45 to 75 seconds

Server warm in tab 1. Cold TUI start is instant; model load stays off
camera.

1. Tab 1 visible for a beat: llama-server idle on 127.0.0.1:9017.
2. Tab 2: `chess-tui`. Home screen, your name and record.
3. `/new`. Coin toss lands; if Gemma opens, its first move and quip
   arrive on their own, which is the better take.
4. One exchange: your move, `Gemma is choosing...`, the reply with
   highlighted squares and a dry comment.
5. `/history`, `1`, enter through a few plies with stored comments.
6. `/back`, `/back`, hold on the record line.

## One-line Termux smoke check

With the server warm, before trusting the setup:

```bash
printf "/new\ne2e4\n/quit\n/quit\n" | chess-tui --name smoke
```

Prints the home screen, a game frame (either your empty board or
Gemma's opening move, depending on the toss), and exits cleanly. A
misaligned board means the terminal is under 40 columns or a font
substitution broke spacing.

Stated plainly: this build was validated against real llama.cpp and
the exact Gemma 4 Q4_0 GGUF on desktop Linux, in both colors, and the
first build was field-tested by Ramon on the target phone. The round
two changes (grammar constraint, bigger board, slash commands, names,
coin toss, port, alternate screen) have not yet run on the phone;
the smoke command above is the check.

## Provenance of the committed screenshots

`tui/screenshots/*.svg` and `.txt` are frames captured from the real
App during acceptance (real actions and rendering, scripted
transport, recording console): the tall board at 48x32 and 60x28, the
single-height board at 40x22 and 80x24, Gemma opening as White, the
two failure states, home, history, and replay. The SVG terminal theme
uses the deck's chalk tokens, the same palette the TUI itself
renders. The live suggestion row exists only in a real raw-mode
terminal, so it appears in the pty acceptance transcript rather than
these frames.
