# Learning guide: phase 27, the clock and the price of quitting

This phase added two small features and one opinion. The features: a
match timer (five minutes by default, thirty tops) and a Start over
button. The opinion, borrowed from Duolingo: quitting costs you.
Start over records a loss before it hands you a fresh board. The
clock running out records a loss. Winning is free. Everything else
has a price, and the W/L/D record under the board keeps receipts.

## Why punish the quit at all

Think about what the button is for. Nobody needs help abandoning a
chess game; browsers have a close button. The problem is the moment
mid-workshop when the bot is up a queen and the human quietly stops
playing, and with them stops generating moves, dataset rows, and
Analysis calls, which is the entire point of the page. Duolingo
figured out that the way to keep people in an uncomfortable exercise
is to make leaving cost something they can see. Here the cost is one
integer in a table, and it works for the same reason: the record is
visible, and now the humiliating defeat is merely probable while the
loss on quit is certain. You keep playing. The dataset keeps growing.

There used to be a Stop game button. It is gone, and the question
worth asking is why removing it was necessary rather than optional.
Put a free exit next to a paid one and watch which gets clicked. A
penalty with a bypass is a suggestion.

## Where the game had to live

Before this phase, "playing against the model" was a boolean in React
state. Reload the page, the boolean is gone, the match evaporates. A
timer makes that arrangement untenable in an interesting way: a clock
that resets when you reload is not a clock, it is a snooze button.

So ask the architecture question the way the codebase does: who owns
durable workshop state? The backend. Hence a `games` table: one row
per match, started_at, time limit, result. The frontend's countdown
is just a rendering of `seconds_left`, a number the server computes
at response time. When the client's clock hits zero it does not get
to declare the loss; it asks, and POST /game/timeout checks the
server's own clock before recording anything. A client that lies
about time gets a 409. This matters because attendees are curious
people with devtools open.

The subtle piece is `expire_if_over`, which runs on every read. Close
the laptop mid-match, come back after lunch, and the GET that renders
your workspace quietly converts the long-dead game into the timeout
loss it earned. Nothing polls, nothing schedules. Why is a lazy check
enough here, when a chess site would need a real scheduler? Because
nothing in this system needs to *react* to the flag falling; the
loss only needs to be true by the next time anyone looks.

## The PGN leak that a timer forced us to fix

A fresh match starts from the starting position, which resets the
board mid-history. The moves table, though, keeps everything, because
those rows are the dataset and deleting data to reset a board would
be trading the workshop's product for its prop. Here is the trap:
the PGN-prefix dataset rows were built from *all* of a workspace's
moves. Start a second game and its first row would carry the previous
game's moves as prefix. Quietly wrong training data, the worst kind.

The fix is a nullable `moves.game_id` and one SQL idiom worth
memorizing: `game_id IS ?`. Plain `= ?` fails on NULL (free-play
moves have no game), while IS is SQLite's NULL-safe equality, so one
query serves both worlds. Ply allocation got the same scoping, so
each match numbers its own moves from zero. Ask yourself what else
in the schema silently assumed one-workspace-one-game forever. That
assumption held from phase 1 until the moment a second game could
exist, which is how schema assumptions always die: not wrong, just
outlived.

## One effect to move the model

The model used to reply because handleMove called it after your
move. Now it replies because an effect notices the board: active
game, black to move, model answers. Same observable behavior, but
the reload case comes free. If you refresh while it is the model's
turn, the effect fires on mount and the match resumes itself; no
"resume" code exists anywhere, resuming is just what rendering the
truthful state does.

Two dependency-array decisions in that file repay study. The
countdown effect keys on `game?.id`, not `game`, because status
refetches produce new objects for the same game and a deadline that
restarts on every refetch never fires. And the turn effect leaves
`modelThinking` out of its deps: an illegal model reply leaves the
turn at black with thinking flipping true to false, and with the flag
in the deps that flip would refire the effect and retry the model
forever, at real API prices. Effects re-run on dependency changes,
so a dependency list is a statement about *when*, not just *what*.
Both lines carry comments saying exactly this, because the linter
disagrees and the linter is usually right, which is what makes the
exceptions worth documenting.

## What the tests pin down

The backend tests play real chess at the rules' edges: fool's mate
(the model mates you, result "loss"), reversed fool's mate (you mate
it, "win"), a backdated started_at standing in for the passage of
five minutes, since tests should not sleep and the clock math never
asks *how* the time passed. The routes tests confirm the paranoid
bits: flagging early is a 409, moving after the flag is a 409 and
the loss sticks. And the browser run against the mock model closed
the loop: start, play, confirm-to-lose, reload to a running 0:11
clock, watch the flag fall, and find the record reading W 0 L 2 D 0,
which is honestly also how my games against real engines end.
