# Phone chess TUI

A small terminal chess app for the workshop opening recording. It runs
on an Android phone inside Termux, talks to a llama.cpp server on the
same phone over the OpenAI-compatible Chat Completions API, and plays
you (White) against Gemma 4 (Black). One screen at a time, typed moves,
persistent record and replay.

The code lives in `tui/`, a self-contained uv project. It never
imports the workshop backend and keeps working if the whiteboard stack
is absent.

## Runtime facts, checked 2026-07-21

- llama.cpp server docs (tools/server/README.md) confirm
  `POST /v1/chat/completions`, `GET /health`, `GET /v1/models`,
  `--reasoning off`, model chat templates from GGUF metadata, and
  `response_format` with `json_schema`. Verified live against a source
  build of commit `76f46ad` (2026-07-20, release b10075 era): the
  OpenAI-style nested shape
  `{"type": "json_schema", "json_schema": {"schema": ...}}` is
  accepted and grammar-constrains output, `pattern`, `maxLength`, and
  `enum` included.
- The move schema constrains `move` to an enum of the turn's actual
  legal UCI moves, not merely a UCI-shaped pattern. With the pattern
  alone, live Gemma 4 E2B anchored on the SAN column and grammar
  decoding padded its intended "e5" into pattern-valid junk ("e5b5"),
  twelve attempts in a row. With the enum, the same intent decodes to
  the listed "e7e5" and every acceptance turn applied on the first
  attempt. The application still validates membership on every reply;
  the decoder constraint is an optimization, not the authority.
- Gemma 4 has a real system role and thinking control tokens. The
  server owns both through the model's chat template and
  `--reasoning off`; the TUI sends plain `messages` and never writes
  Gemma control tokens.
- The deployment model is `google/gemma-4-E2B-it-qat-q4_0-gguf`
  (file `gemma-4-E2B_q4_0-it.gguf`, 3.35 GB, QAT Q4_0, 2.3B effective
  parameters). The repo also ships `gemma-4-E2B-it-mmproj.gguf`; this
  text-only game never loads it (`--no-mmproj`).
- llama-cpp-python is not used. Its own README says Docker on rooted
  Termux is "currently the only known way to run this on phones".
  The native server is already on the phone; HTTP wins.
- uv has no Termux package and fails to build on aarch64-linux-android
  (astral-sh/uv#2705, termux/termux-packages#21096). The phone path is
  plain pip in a venv; uv is the desktop path.
- The UI is Rich plus a frame-render input loop, not Textual. Textual
  has documented Termux install failures through its tree-sitter
  extras (Textualize/textual#5644) and slow phone cold starts, and the
  implementing agent could not run the required on-device smoke test.
  Plain ANSI plus blocking `input()` has no terminal-capability
  dependencies beyond color, which degrades cleanly. One UI
  implementation only.

## Termux setup

Prerequisites on the phone: Termux from F-Droid, llama.cpp installed
and working (`pkg install llama-cpp` or a local build per the llama.cpp
Android docs), and Python 3.11+.

```bash
pkg update
pkg install git python
git clone <this repo>
cd <repo>
python -m venv ~/.venvs/chess-tui
source ~/.venvs/chess-tui/bin/activate
pip install ./tui
```

Everything the TUI needs is pure Python (python-chess, httpx, rich);
nothing compiles. On a desktop, use uv instead:

```bash
uv sync --project tui
uv run --project tui chess-tui   # or: just phone-tui
```

Stated plainly: this build was validated against real llama.cpp and
the exact Gemma 4 Q4_0 GGUF on desktop Linux, not on the phone. That
is not Android validation. The one smoke command to run in Termux
before trusting the recording setup, with the server warm in the
other tab:

```bash
printf "new\ne2e4\nquit\nquit\n" | chess-tui
```

A healthy install prints the home screen, the board with 1. e4,
`Gemma is choosing...`, Gemma's reply and comment, and the record
screen, then exits. If the board renders misaligned, the terminal is
narrower than 40 columns or a font substitution broke spacing; shrink
the font one step and rerun.

## Start the server, then the TUI

Termux tab 1, the model server. Tested command:

```bash
llama serve \
  -hf google/gemma-4-E2B-it-qat-q4_0-gguf:Q4_0 \
  --alias gemma-4-2b-local \
  --host 127.0.0.1 \
  --port 8080 \
  --no-mmproj \
  --reasoning off \
  -c 4096
```

The first run downloads the 3.35 GB GGUF into the llama.cpp cache.
`-c 4096` keeps the context allocation phone-sized; a chess turn uses
well under 2k tokens. Wait for the server to answer
`curl -s http://127.0.0.1:8080/health` with `{"status":"ok"}` before
recording anything.

Termux tab 2, the game:

```bash
source ~/.venvs/chess-tui/bin/activate
chess-tui
```

## Playing

The home screen shows your record and the capture count in won games.
Commands are typed words, no function keys, no mouse:

```text
new      start a game. you are White and move first
e2e4     moves as UCI
Nf3      moves as SAN. promotion: e7e8q or e8=Q
retry    repeat a failed model turn
flip     turn the board around (never flips by itself)
history  past games, newest first
replay   step through a stored game (next, prev; enter is next)
help     the command list
quit     leave the screen. at home, exit
```

While Gemma thinks the screen says `Gemma is choosing...`. A model
that answers garbage gets exactly one corrective request naming the
rejection; if that also fails you see

```text
Gemma did not return a legal move. retry or quit
```

with the exact reason underneath, and the board unchanged. A dead or
timing-out server is its own visible state, same recovery. No
fallback move is ever attributed to Gemma.

## Configuration

Defaults suit the phone. Environment variables, with equal CLI flags:

```text
CHESS_TUI_BASE_URL=http://127.0.0.1:8080/v1   --base-url
CHESS_TUI_MODEL=gemma-4-2b-local              --model
CHESS_TUI_API_KEY=local                       --api-key
CHESS_TUI_TIMEOUT=120                         --timeout
CHESS_TUI_DB=<path>                           --db
NO_COLOR=1                                    --no-color
```

The API key is sent as a bearer header and nowhere else: never stored,
never displayed, absent from the SQLite file (tested by scanning the
db bytes). The local server does not need a real credential.

Games live in SQLite under the XDG data directory,
`~/.local/share/chess-tui/games.db` on Termux and Linux. Every ply
stores FEN before and after, every model reply is kept raw with
request id and latency, and replay renders exactly what was stored.
Model comments are model commentary, not engine analysis; nothing is
ever labelled a mistake because nothing evaluates moves.

## Measured shape of a turn

Numbers from the desktop acceptance build (llama.cpp `76f46ad`, CPU,
4 threads, x86); phone magnitudes will differ but the shape holds:

- App cold start to a rendered home screen: 0.3s. Model load is the
  slow part: about 3 to 9s with the GGUF in page cache, longer cold.
- One move turn end to end: 2.4 to 10.5s. A turn sends roughly 540
  prompt tokens and receives about 30.
- The recording should start after `/health` returns `{"status":"ok"}`
  and one warm-up move has been played off camera.

## Troubleshooting

- "server unreachable. retry or quit": the server tab died. Check
  `curl -s http://127.0.0.1:8080/health`, then `retry`.
- "server error. retry or quit" with `HTTP 503 Loading model`: the
  server is up but still loading the GGUF. Wait for `/health` to say
  ok, then `retry`; the same turn repeats.
- "Gemma timed out. retry or quit": the phone is thermal-throttling or
  the model is cold. Raise `--timeout`, keep the server warm, `retry`.
- Wrong model alias: the TUI sends `gemma-4-2b-local`; if `llama serve`
  runs without `--alias gemma-4-2b-local`, llama.cpp still answers with
  its loaded model, but keep them matched so the recorded provenance
  is honest. `curl -s http://127.0.0.1:8080/v1/models` shows the alias.
- Narrow terminal: the board is 22 columns and the layout is designed
  down to 40x22. Below that, lines crop rather than wrap; shrink the
  Termux font one step.
- Unicode width: not an issue by construction. Pieces are ASCII
  letters, uppercase White, lowercase Black, readable in monochrome.
  There is no Unicode piece mode because single-cell width on the
  target device was not verifiable; letters survive any font.
- Colors look flat: your terminal or NO_COLOR stripped them. The game
  is fully playable without color; case carries the piece distinction.

## Recording shot list, 45 to 75 seconds

Server warm in tab 1 before recording starts. Cold TUI start is
fast; model load is the slow part and stays off camera.

1. Tab 1 visible for a beat: `llama serve` output idle on 127.0.0.1.
2. Switch to tab 2, run `chess-tui`. Home screen with the record.
3. `new`. Clean board, `You: White | Gemma: Black | move 1`.
4. Type `e2e4`. Board updates, `Gemma is choosing...`, reply lands
   with the highlighted squares and a dry comment.
5. One more exchange if the pace allows.
6. `quit`, `history`, `replay 1`, tap enter through a few plies with
   the stored comments.
7. `quit` twice to the home record screen. Hold on the record line.

## Provenance of the committed screenshots

`tui/screenshots/*.svg` and `.txt` are frames captured from the real
App during acceptance (real actions and rendering, scripted transport,
recording console), at 40x22, 48x24, 60x28, and 80x24, plus the two
failure states, home, history, and replay. The SVG terminal theme uses
the deck's chalk tokens, the same palette the TUI itself renders.
