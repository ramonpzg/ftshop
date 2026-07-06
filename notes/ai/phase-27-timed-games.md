# Handover: phase 27, timed games and the start-over-is-a-loss rule

Written 2026-07-06. Read phases-25-26 first; this builds on the
workspace layout and the model opponent from phases 19-23.

## What was built

**A durable game entity.** New `games` table (id, workspace_id,
time_limit_seconds, started_at, ended_at, result) plus a nullable
`moves.game_id`. init_db patches game_id into pre-existing databases
with an ALTER TABLE, so a live workshop DB survives the upgrade
without reset-db. Being durable fixes the old deferred item: opponent
state is no longer client-side, a reload resumes the match, clock and
all.

**The rules.** One clock per match: default 300 seconds, choices up to
1800, validated on both the pydantic model and in the action. Start
game begins a fresh match from the starting position (it used to arm
auto-reply from wherever the board stood). The only exits from a
running match: win it (checkmate ends the game, either direction, and
a stalemate draws it), let the flag fall (loss_timeout), or click
Start over (loss_resign, and a new game starts on the same clock).
There is no Stop button anymore, deliberately: a free exit next to a
punishing one makes the punishing one decorative. Ramon's Duolingo
framing, implemented literally.

**Enforcement lives server-side.** `actions/games.py` owns the
lifecycle (start_game, start_over, flag_timeout, game_status), all
returning a GameStatus dataclass (workspace, active game, W/L/D
record). `expire_if_over` lazily reconciles a stale game with the
wall clock on every read, so a reload after lunch shows the timeout
loss it earned. make_move refuses moves on an expired clock (409),
stamps game_id on each move, and ends the game on mate; model_move
passes mover="model" so its mates record as your loss. The
seconds_left field is computed server-side at response time, so the
client never trusts its own clock across a reload, and
POST /game/timeout verifies expiry before recording anything: a
client cannot flag its own game early.

**PGN scoping.** list_legal_sans and the ply allocation are scoped by
game_id (`game_id IS ?` handles the free-play NULL), so a fresh match
starts its PGN prefix at move one instead of inheriting the whole
workspace history. Free play (no game) behaves exactly as before.
reset_page deletes games along with moves and dataset rows.

**Frontend.** `lib/gameClock.ts` holds the pure bits (formatClock,
describeGameEnd, TIME_LIMIT_CHOICES). The board section shows: a
duration picker + Start game when idle; a ticking mm:ss clock + Start
over when playing; a two-step confirm ("Starting over counts as a
loss." / Confirm loss / Keep playing); the W/L/D record; and a notice
line for every ending. The countdown interval flags the timeout at
zero and lets the server confirm. The model-reply trigger moved from
handleMove into one effect keyed on "active game and black to move",
which covers both normal replies and resuming a reloaded match.

**Verified end to end** against the mock OpenAI server: start, model
reply, confirm-to-lose (record L1, board reset, fresh clock), reload
mid-match resuming at 0:11, and a real flag fall (record L2, "Time
ran out. That is a loss.", Start game back). 244 backend + 133
frontend tests.

## Intentionally deferred, and why

- **Draw detection covers stalemate only.** Insufficient material,
  repetition, and the fifty-move rule play on until someone's clock
  dies. python-chess can detect all of them; nobody at a workshop
  will hit them in five minutes.
- **The clock does not pause while the model thinks.** One shared
  clock is the simple, honest reading of "a default timer of 5
  minutes per match". Per-side clocks are a chess.com feature, not a
  teaching device.
- **No win/loss forfeit for abandoning the page.** Closing the tab
  leaves the game running; the clock will convert it to a timeout
  loss on its own. That is the correct Duolingo behavior anyway.

## Known issues / tech debt

- The 500ms countdown interval lives per open workspace panel. A
  viewer never runs it (status is only fetched for the owner), but
  the owner having the same workspace open in two tabs would race to
  flag the timeout; the server-side verify makes the race harmless,
  one tab just gets a 409 and resyncs.
- The model-reply effect fires when the turn flips to black. An
  illegal model reply leaves the turn at black without refiring the
  effect, so the match stalls until the player clicks Start over.
  Same behavior as before this phase, now with a paid exit.
- e2e smoke tests do not cover the clock; the scratchpad
  clock-test.mjs script does, but needs the mock OpenAI server up.

## What the next phase should tackle first

1. The standing item: one real rehearsal against api.openai.com.
   gpt-5.5-mini latency eats clock time, which is now a game
   mechanic; five minutes may feel very different at real latency.
2. Consider surfacing the record on the attendee panel (a leaderboard
   is one query away: games grouped by workspace).
3. The fallback notebook does not know about timed games. A short md
   cell stating the rule would keep the 1:1 mapping honest.

## Gotchas

- `game_id IS ?` in SQLite is the NULL-safe equality; binding None
  compares correctly where `= ?` would not. Both the ply subquery and
  list_legal_sans rely on it.
- GameOut is built with `GameOut(**dict(row), seconds_left=...)`;
  pydantic's default extra="ignore" silently drops the row's
  created_at. If you add a field to the games table and wonder why it
  is not in the API, that is why.
- In the countdown effect, the deps are `[game?.id, isOwnWorkspace]`
  on purpose. Keying on the game object would restart the deadline on
  every status refetch; keying modelThinking into the turn effect
  would retry an illegally-replying model forever.
- The mock OpenAI server answers the first move in the legal-moves
  list it is shown (Nh6 after 1. e4, with python-chess ordering). Do
  not write assertions against a specific reply move.
