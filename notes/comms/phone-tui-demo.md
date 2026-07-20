# Urgent implementation prompt: phone-first chess TUI

## Prompt

You are building a small, reliable chess TUI for the EuroSciPy 2026 workshop
repository. Its primary environment is an Android phone running Termux. Ramon
will run llama.cpp in one Termux tab, run the TUI in a second tab, play a short
game, and record the screen for the opening deck.

This is a real application and a recording target, not a mockup. Optimize for
the shortest route from a fresh clone to a readable, repeatable recording.
Keep the scope narrow. The phone already has native llama.cpp; the TUI should
normally connect to its localhost OpenAI-compatible Chat Completions API.
Pragmatism beats visual flourish. Use the fewest dependencies and the least
code that produce a readable board, a correct game loop, persistence, and
replay. Do not add an abstraction or effect merely because a desktop TUI could
support it.

### Branch and repository boundaries

- Start from the current accepted `main`, after phase 33 is merged, and create
  `demo-termux-chess-tui`.
- Read `AGENTS.md`, `CLAUDE.md`, `docs/architecture.md`, and the final phase 33
  handover before editing.
- Add the application under a new top-level `tui/` directory with its own
  minimal `pyproject.toml` and lockfile. Do not make a phone install resolve
  FastAPI, Jupyter, torch, audio, web, or deck dependencies.
- Do not read, edit, export, or regenerate anything under `notebooks/` or
  `web/public/notebooks/`.
- Do not redesign or edit the Slidev deck. Ramon will record the finished TUI
  and place the video later.
- Use the repository's actions/calculations/data split inside the TUI. Screen
  widgets render and dispatch. They do not parse model output, adjudicate
  chess, construct prompts, or write SQLite directly.
- Add coherent commits throughout, push the branch, and do not merge it.
  Finish with a clean tree and the required handover and learning guide.

## 1. Research the current runtime before choosing flags

This work is sensitive to very recent llama.cpp and Gemma 4 behavior. Do not
implement it from remembered Gemma 3, old `llama-server`, or OpenAI SDK
examples.

Read these current primary sources before coding:

- llama.cpp server documentation:
  <https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md>
- llama.cpp Android/Termux documentation and current build notes:
  <https://github.com/ggml-org/llama.cpp/wiki/Android-Termux>
- the current llama.cpp repository and relevant release/changelog entries:
  <https://github.com/ggml-org/llama.cpp>
- Gemma 4 model overview:
  <https://ai.google.dev/gemma/docs/core>
- Gemma 4 prompt formatting, system-role, and thinking controls:
  <https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4>
- the exact deployment model card and file list:
  <https://huggingface.co/google/gemma-4-E2B-it-qat-q4_0-gguf>
- llama-cpp-python's current installation and server documentation only to
  assess, not assume, its Termux viability:
  <https://github.com/abetlen/llama-cpp-python>

Record the access date, llama.cpp commit or release tested, exact Gemma file or
Hugging Face selector, server command, and relevant findings in
`docs/phone-tui.md` and the handover.

Verify at implementation time that the current server still supports:

- `POST /v1/chat/completions`;
- the model's native chat template and Gemma 4 system role;
- `--reasoning off` or the then-current equivalent;
- JSON object or JSON-schema constrained output;
- `/health` and `/v1/models`, if the client uses them.

Do not use the Responses API. Do not manually write Gemma control tokens when
llama.cpp's model chat template already owns formatting. Do not load the
multimodal projector for this text-only game.

### Runtime decision

Use native llama.cpp serving plus a small HTTP client as the default:

```text
Termux tab 1: llama.cpp server on 127.0.0.1
Termux tab 2: Python TUI -> POST /v1/chat/completions
```

Do not add `llama-cpp-python` to the default phone install. Its upstream
support and native build requirements on Termux have historically been
fragile, while the native server is already installed and working on Ramon's
phone. Use the Python binding only if you reproduce a straightforward native
Termux install on the target architecture and can show that it is simpler than
the HTTP process. Do not use Docker on the phone.

Document a tested server command based on the current CLI. Its intended shape
is:

```bash
llama serve \
  -hf google/gemma-4-E2B-it-qat-q4_0-gguf:Q4_0 \
  --alias gemma-4-2b-local \
  --host 127.0.0.1 \
  --port 8080 \
  --no-mmproj \
  --reasoning off
```

Do not copy this blindly if the current CLI differs. Keep the host on
`127.0.0.1`; the TUI and model run on the same phone. Add only measured context
or thread flags. Avoid a giant context allocation for a chess move request.

## 2. Keep the phone installation small

Prefer a minimal Python 3.11+ application with:

- `python-chess` for every rule, move, result, and replay calculation;
- `httpx` for the localhost Chat Completions request;
- Textual for the interface if its current release installs and renders
  correctly in Termux without compiled extras;
- standard-library SQLite for persistence.

If Textual fails a real Termux smoke test, use Rich plus a simple input loop or
standard curses. Do not keep two UI implementations. Record the reason for the
choice.

Support both setup paths when practical:

```bash
uv sync --project tui
uv run --project tui chess-tui
```

and a conventional Termux virtual environment using `pip`. Add `just phone-tui`
and focused install/test recipes, but do not make the phone require `just`.

Default configuration:

```text
CHESS_TUI_BASE_URL=http://127.0.0.1:8080/v1
CHESS_TUI_MODEL=gemma-4-2b-local
CHESS_TUI_API_KEY=local
```

Expose equivalent CLI flags. Normalize a trailing slash once. Never persist or
display the API key. The default server does not need a real credential.

## 3. Design for a portrait phone terminal

The recording must be understandable before it is attractive. Design and test
at 40x22, 48x24, 60x28, and a normal desktop terminal. One screen at a time.
No desktop dashboard, sidebars, mouse dependency, or tiny secondary panels.

The game screen has this vertical order:

1. one compact status line: `You: White | Gemma: Black | move 8`;
2. the board;
3. last move and game state (`...e5`, `check`, `white won`, and so on);
4. at most two wrapped lines of Gemma commentary;
5. one move/command input line.

Render White at the bottom by default. Provide a flip command, but never flip
automatically. Files and ranks must remain visible:

```text
    a b c d e f g h
 8  r n b q k b n r  8
 7  p p p p p p p p  7
 6  . . . . . . . .  6
 5  . . . . . . . .  5
 4  . . . . P . . .  4
 3  . . . . . . . .  3
 2  P P P P . P P P  2
 1  R N B Q K B N R  1
    a b c d e f g h
```

Use uppercase for White and lowercase for Black even when Unicode pieces and
color are enabled. That invariant makes the board readable under a broken
font, monochrome recording, or poor projector. Unicode pieces may be the
default only after verifying stable single-cell width in Termux. Provide an
ASCII mode and honor `NO_COLOR`.

Use restrained ANSI square backgrounds where supported. Highlight the source
and destination of the last move. Do not let color carry meaning by itself.
Keep every cell at a stable width so a check label or selection cannot shift
the board.

Phone keyboards make typed moves more reliable than cursor choreography. The
main input accepts UCI (`e2e4`) and SAN (`Nf3`). It also accepts these terse
commands:

```text
new  history  replay  retry  flip  help  quit
```

Do not require function keys, mouse clicks, hover, or simultaneous key chords.
Arrow-key replay is optional; `next` and `prev` commands must work.

## 4. Build a truthful game loop

For the recording-ready first version:

- the participant is White and moves first;
- Gemma is Black;
- `python-chess` is the sole authority for legal moves, SAN/UCI conversion,
  check, checkmate, draw, promotion, and final result;
- the model receives the current position and legal choices but never gets to
  alter board state directly;
- every accepted move is persisted before the next network call;
- one model call is in flight at a time;
- the UI remains responsive and shows `Gemma is choosing...` while waiting;
- transport, parsing, illegal-reply, and server-unavailable failures are
  distinct visible states.

Do not add clocks, accounts, networking between phones, Stockfish, opening
books, cloud fallback, or model downloads inside the TUI. They are not needed
for the recording.

### Move request

Each model turn is a fresh, bounded request. Do not replay a growing assistant
conversation when FEN and compact history contain the required state. Send:

- one versioned system message;
- one user message containing the FEN, compact PGN or SAN history, White's
  latest move, and every legal Black move as `UCI | SAN`;
- a JSON response constraint supported by the tested llama.cpp version;
- `stream: false` for the first version;
- a documented timeout suitable for phone inference.

Do not send `reasoning_effort` to llama.cpp. Thinking is controlled by the
tested Gemma 4/llama.cpp mechanism, preferably the server's `--reasoning off`.
The visible response must not contain internal reasoning.

### System prompt

Start from this prompt. Keep it in a dedicated calculation module with an
explicit version. Change it only after a real Gemma 4 test demonstrates why.

```text
You are Black in a legal chess game and a terse, dry chess coach.

The application is the only authority on the board and the rules. On every
turn it gives you the current FEN, the game history, White's latest move, and
the complete set of legal Black moves.

Choose exactly one move from LEGAL_MOVES. Copy its UCI value exactly. Never
invent a move, alter a move, claim that an unlisted move is legal, or return
more than one move.

Prefer, in order: checkmate; preventing forced loss; checks and forcing moves;
sound development and king safety; plans that can win while avoiding
unnecessary captures. Never avoid a necessary capture merely to satisfy the
last preference.

Write one short comment about the move or White's preceding move. Be dry,
confident, and a little smug. Tie the comment to the actual position. Do not
use motivational filler, chess cliches, slurs, threats, identity-based
insults, or claims of engine certainty. Keep the comment under 90 characters.

Return one JSON object and nothing else:
{"move":"<exact legal UCI>","comment":"<one short sentence>"}

Do not use Markdown, code fences, analysis, reasoning, or additional keys.
```

The user message uses a stable shape such as:

```text
FEN: <fen>
HISTORY_SAN: <compact history or ->
WHITE_LAST_MOVE: <uci> | <san>
LEGAL_MOVES:
- e7e5 | e5
- e7e6 | e6
...

Return the required JSON object.
```

Use a JSON schema when the tested llama.cpp build supports it. The schema
requires exactly `move` and `comment`, disallows extra properties, constrains
the move to a UCI-shaped string, and limits comment length. The application
still validates the parsed type and membership in the actual legal-move set;
schema output does not replace chess validation.

### Failure policy

Persist every raw reply and its result: applied, malformed JSON, wrong shape,
illegal move, transport failure, or timeout. Never store authorization
headers.

If Gemma replies but the reply is malformed or illegal, make one corrective
request that includes the rejected response, says exactly why it failed, and
repeats the unchanged legal list. If that also fails, do not silently play a
fallback. Leave the board unchanged and show:

```text
Gemma did not return a legal move. retry or quit
```

A server failure likewise leaves the board unchanged. `retry` repeats the
same turn. This makes failures visible and keeps the recording recoverable
without attributing an invented move to the model.

## 5. Persist stats and replay without pretending to be Stockfish

Use SQLite under the platform's XDG data directory, with a configurable path
for tests. Persist:

- game ID, start/end time, model alias, prompt version, result, and duration;
- every ply's UCI, SAN, FEN before/after, actor, timestamp, and capture flag;
- Gemma's comment, raw reply, request ID where available, latency, and attempt
  status;
- aggregate wins, losses, draws, completed games, and captures by the player.

The home screen shows the record and offers `new`, `history`, and `replay`.
History is a compact newest-first list. Replay opens one game, renders the
board at each ply, highlights the last move, and shows the recorded comment.

Do not label moves as mistakes without Stockfish or another explicit
evaluator. Use `Replay` or `Review moves`, not `Find mistakes`. Model comments
are model commentary, not verified engine analysis.

The personal objective is visible as a secondary statistic: wins and the
number of opposing pieces captured in those wins. Do not change chess scoring
or sacrifice checkmate to optimize that statistic.

## 6. Keep boundaries small and testable

Suggested ownership:

```text
tui/src/chess_tui/actions/       game orchestration, model turn, replay
tui/src/chess_tui/calculations/  board view, prompt, parsing, stats
tui/src/chess_tui/data/          llama.cpp HTTP client, SQLite repos, config
tui/src/chess_tui/ui/            screens and widgets
```

Do not import the workshop FastAPI application. Reuse a small pure calculation
only when extracting it creates less coupling than copying a stable format.
The phone TUI must continue to run if the whiteboard backend is absent.

Tests must cover:

- UCI and SAN participant input, including promotion;
- rejection of illegal participant input without changing the board;
- exact board rendering and alignment at every target phone width;
- White/Black distinction in ASCII and no-color modes;
- prompt construction from a real `python-chess` position;
- JSON object validation, scalar/list JSON rejection, code-fence handling only
  if deliberately supported, and legal-list membership;
- first malformed reply followed by a valid corrective reply;
- two invalid replies leaving the board unchanged with retry available;
- transport failure and timeout recovery;
- checkmate, stalemate, repetition, resignation if implemented, and persisted
  result statistics;
- SQLite reload and replay reproducing every stored board position;
- model comments and raw replies surviving reload;
- no API key or header written to disk or diagnostics.

Use `httpx.MockTransport` or a tiny local HTTP test server for the transport
boundary. Do not mock `python-chess` or the complete game action.

## 7. Manual and visual acceptance

Before claiming completion:

1. Run the TUI against a real current llama.cpp server and the exact Gemma 4
   Q4_0 model.
2. Play enough legal moves to show at least two model turns.
3. Restart the TUI and replay the persisted game.
4. Stop the server mid-turn and prove the board remains intact with a usable
   retry state.
5. Capture screenshots at 40x22, 48x24, 60x28, and 80x24. Check board columns,
   wrapped commentary, prompts, errors, history, and replay.
6. Test in real Termux on the target phone. If the implementing agent cannot
   access the phone, state that plainly and provide one exact smoke command
   Ramon can run. Do not report desktop Linux as Android validation.
7. Time cold app start separately from model load. The recording should start
   after the server is warm.

Write `docs/phone-tui.md` with:

- exact Termux prerequisites and install commands;
- exact tested llama.cpp server command;
- how to start, play, retry, inspect history, and replay;
- configuration and data location;
- troubleshooting for server unavailable, wrong model alias, narrow terminal,
  and Unicode width;
- a 45 to 75 second recording shot list.

The recording shot list should show the result, not installation:

1. server already warm in tab 1;
2. open TUI in tab 2;
3. home record;
4. new game and clear board;
5. one White move and one Gemma reply/comment;
6. history and replay;
7. final record screen.

Run the focused TUI lint, typecheck, tests, and packaging check, then the
repository's normal `just lint`, `just typecheck`, and `just test`. Add the TUI
to those normal command surfaces without making unrelated dependency groups
install on the phone.

## Documentation and report

Create:

- `notes/ai/phone-tui-demo.md`
- `notes/hu/phone-tui-demo.md`

The handover must record the exact source versions consulted, runtime choice,
Termux result, server/model command, prompt version, screen sizes inspected,
real model responses observed, known performance limits, and the recording
steps. The learning guide should explain why python-chess owns legality, why
the model receives a legal set, why structured output still needs validation,
and why replay is evidence while unverified "mistake detection" is a claim.

Finish with a concise inventory of files, commands, dependencies, tests,
screenshots, real-device checks, and anything Ramon must do before recording.
