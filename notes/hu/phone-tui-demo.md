# Learning guide: the phone chess TUI

You now own a chess app that runs in a phone terminal, plays against a
2B model served from the same phone, and never once lets that model
touch the rules. This guide walks through why it is shaped the way it
is, with the usual detours where you get to do the thinking.

## Who is allowed to know chess

Start with a question. The model receives the FEN, the history,
White's last move, and every legal Black move with both spellings. Why
hand it the legal list at all? Gemma has seen millions of games. It
knows how knights move, roughly, the way you know the lyrics to a song
you have heard through a wall.

Think about what happens without the list. The model produces
something move-shaped. Now you need to decide whether it is legal, so
you ask python-chess, which means python-chess was the authority all
along and you just let the model waste its tokens guessing at
something you already knew. Sending the list converts the task from
"generate a legal move" (hard, hallucination-prone) to "copy one item
from this menu" (nearly mechanical), and the failure mode from "subtle
illegal move that poisons the game" to "string not in set", which a
set-membership check catches in constant time. The model's job is
picking a good item and being smug about it. The application's job is
everything else.

That split is the same actions, calculations, data discipline the
backend uses, shrunk to fit a phone. `calculations/` holds the pure
stuff: board rendering to a cell grid, prompt text, reply judgment,
input parsing, record math. `data/` does I/O and nothing clever: three
small repo modules, a config loader, one httpx client. `actions/`
composes them and owns every transaction. `ui/` renders lines and
dispatches typed commands. If you want to know whether a reply is
valid, there is exactly one function to read, and it does not need a
network to be tested.

## The schema is a seatbelt, not a driver's license

The request asks llama.cpp for grammar-constrained JSON: an object
with exactly `move` and `comment`, no extra keys, comment bounded.
The first version constrained the move to a UCI-shaped regex, which
sounds sufficient until you watch a real model wear it. During live
acceptance, Gemma read the legal list, decided on the classical reply
to 1. e4, and reached for "e5". That is the SAN spelling. The grammar
demanded four squares, so decoding padded the model's two intended
characters into pattern-perfect garbage: `e5b5`, twelve attempts in a
row, corrective requests bouncing off it. Nothing was broken in the
transport, the prompt, or the parser. The constraint itself was
warping intent into legal-looking nonsense.

Sit with that failure for a second, because it generalizes. A grammar
does not make a model right; it forces whatever the model was going
to say into the nearest permitted string. If the permitted set
includes junk, you get confident junk. The fix was to stop permitting
junk: the schema now constrains `move` to an enum of the turn's
actual legal UCI moves. The same probability mass that wanted "e5"
now lands on `e7e5`, because that is the only legal continuation
spelled anything like it. After the change, every live turn applied
on the first attempt.

Ramon's phone then supplied the sequel. His Termux llama.cpp build
silently ignored `response_format` altogether, free-ran every reply
to the 192-token cap, and handed back an unlisted move on the first
turn, which is how we learned that the OpenAI-shaped schema field is
the newer, less portable spelling of the same idea. The constraint
now ships as a raw GBNF `grammar` field, llama.cpp's own mechanism
and years older than json_schema support, enumerating the legal menu
inside the fixed JSON shape. Same trick, lower in the stack, works on
old builds, and as a bonus generation stops at the closing brace,
about 35 tokens instead of 192, which on a phone is the difference
between seven seconds and seventeen.

So why does `judge_move_reply` still check everything, membership
included? Because the grammar lives on the server, and servers
change, downgrade, or get swapped for one that ignores the field.
An application that trusts a remote validator has no validator. The
seatbelt keeps the reply parseable and steers it toward the menu;
the license to move a piece is issued by python-chess alone, on
every reply, forever.

Here is the judgment, condensed:

```python
parsed = extract_json_object(raw)          # fences tolerated, on purpose
move = parsed.get("move")                  # must be a string
if not _UCI_SHAPE.match(move) or move not in legal_uci:
    return ReplyVerdict("illegal", move=move,
                        reason=f'move "{move}" is not in LEGAL_MOVES')
```

The reason string matters. It goes back to the model verbatim in the
one corrective request, so the model is told exactly what it did
wrong, with the same unchanged legal list. One correction, not a loop:
a model that fails twice gets its failure shown on screen, board
unchanged, and the human decides. The alternative, quietly playing
some fallback move and attributing it to Gemma, would make the
recording a small lie. The workshop is about evaluating models
honestly; the demo refusing to fake a move is the point.

## Why every move commits before the network call

Trace the participant path: your move parses, applies, persists,
commits, and only then does the model request go out. Why commit
first? Ask what the failure modes are. The phone loses power. Termux
gets killed by Android's memory manager mid-request. The server hangs
for two minutes and you swipe the app away. In every case the game on
disk is exactly the game you saw on screen, because nothing you saw
was ever provisional. The model turn then commits its ply together
with its attempt row, while failed attempts commit individually the
moment they happen. Evidence of failure must survive the failure,
which you will recognize as the same rule the backend's model_attempts
table follows. A failed reply that vanishes with the crash never
happened, and "never happened" is how demos start lying.

Question worth sitting with: the attempt table stores the raw reply,
the parsed move, the request id, the latency, and the failure reason,
but not the request headers. What would storing headers cost? The
Authorization header holds the API key. The test suite scans the raw
database bytes for the key and for the words Bearer and Authorization,
and fails if any appear. Paranoid? The db file syncs to backups,
gets attached to bug reports, gets committed by accident. Secrets
that never touch disk cannot leak from it.

## Rich, not Textual, and why that is not a downgrade

The phase prompt preferred Textual if it renders correctly in Termux.
The repo shipped Rich plus a loop that clears the screen, prints one
frame, and blocks on `input()`. Three reasons, recorded here because
"we used the simpler thing" always sounds like laziness until you see
the constraints.

First, verification. Textual on Termux has documented install
failures through its tree-sitter extras and reports of slow phone
startup, and this work was done without the target phone in hand. You
do not ship an unverifiable framework to a device you cannot test
when the deliverable is a recording with one take. Plain ANSI output
and a blocking read have no failure modes that depend on the terminal
being fancy.

Second, fit. Look at the screen contract: status line, board, state
line, two comment lines, input line. No panels, no focus, no mouse,
nothing concurrent except one spinner while the model thinks. A frame
renderer models that exactly. An async widget tree models a desktop
app that this deliberately is not.

Third, the keyboard. On a phone, typed words beat cursor choreography,
so the input model is the terminal's own line editing, which Android
keyboards already know how to drive. The board is 22 columns of
2-character cells, White uppercase, Black lowercase, and that
invariant holds in full color, in NO_COLOR, and in a monochrome
recording. Color is decoration here; case is information. When the
chalk palette from the deck (`deck/style.css`, the `style-chalk`
tokens) tints the squares and highlights the last move, it is the same
grid, cell for cell. A test renders both and asserts the geometry is
identical, which is the kind of test that sounds trivial until a
styled cell grows a character and the board turns into modern art.

## Replay is evidence, review is a claim

The history screen will happily replay any stored game, ply by ply,
with the model's comments where they were made. It will not tell you
where you blundered. That restraint is deliberate. Finding mistakes
requires an evaluator, something like Stockfish, and nothing in this
app evaluates positions. The comments on screen are what a 2B model
said while picking from a menu, preserved raw in the database. Calling
them analysis would promote commentary into judgment with nothing
underneath.

So the replay says `ply 3/7  2. Qh5` and shows the recorded remark,
and the record screen counts wins and the pieces you captured in wins,
which is your stated personal objective and exactly as meaningful as
you make it. If a future phase wants "find my mistakes", the honest
route is wiring in an engine and labelling its output as engine
output. The dishonest route is asking Gemma to grade your game and
printing it in a serious font.

Last question, and it is the one the whole workshop hangs on. The TUI
could have used a stronger cloud model and hidden the latency with a
spinner. It runs a 4-bit 2B model on a phone instead, and sometimes
that model fumbles a reply and the screen says so. Why is the fumble
worth recording? Because the session is about what adaptation actually
buys you, and a demo that only shows models succeeding has no before
picture. The failure states are not bugs in the demo. They are the
demo.
