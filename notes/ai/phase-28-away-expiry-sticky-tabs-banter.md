# Handover: phase 28, breaking bad news, sticky tabs, match log, banter

Written 2026-07-07, straight off Ramon's feedback on phase 27. Four
items, all shipped.

## What was built

**The away-expiry notice.** A game that times out while nobody is
looking (server restart, closed laptop) used to become a silent loss
in the record. Now GET /workspaces/{id}/game reports
`expired_while_away: true` on exactly the read that lazily converted
the stale game, and the frontend shows "The clock ran out while you
were away. That counts as a loss." The server flag alone was not
enough: React StrictMode double-mounts effects in dev, and the
throwaway first mount ate the one-shot flag. So the client also
remembers the match it was in (localStorage
`euro-chess-studio:active-game:<workspaceId>`, written on every
status apply) and breaks the news itself when that game is gone and
the newest finished game is a timeout. Belt and suspenders; the belt
is tested in pytest, the suspenders in the browser.

**Failed moves say so.** A move request that dies for any reason
other than the 409 clock conflict now shows "That move never reached
the server. Is the backend running?" instead of eating the click.

**Sticky dataset tabs.** DatasetPanel used to render the last six
rows keyed by row id, so every move replaced all six `<details>`
elements and the open one snapped shut, killing the watch-the-rows-
appear moment. It now renders one stable group per dataset shape, in
teaching order, with a count badge and the newest payload inside.
Open state lives in React state keyed by shape, so it survives every
re-render. Open "FEN -> move", play on, and the payload updates in
place while the count climbs. The `maxRows` prop is gone.

**Match log.** `list_finished_games` returns finished games newest
first, each with its legal move count (correlated subquery). The
status payload carries them as `history`, and the board section
lists the last five under the record: "Loss, time. 7 moves on a 5
min clock." `describeMatch` in gameClock.ts owns the wording.

**Banter.** `lib/gameBanter.ts` holds four pun pools: check,
checkmate (the model mated you), win (you mated it), loss (timeout
or start over). `pickBanter(kind, index)` is pure rotation, no
randomness, so tests are deterministic. The component keeps a
counter ref, increments per pun, and reseeds it from total games
played on every status apply so the rotation survives reloads. Wiring:
a checking move drops a check pun, a mating move drops win or
checkmate by mover, every loss path (start over, flag fall, expired
away, 409) drops a loss pun. The banter line renders italic under
the notice, `data-testid="game-banter"`.

**Verified live** against the mock model: open tab stays open across
moves with payload replaced in place; start over shows notice, pun,
and a history line; backdated game plus reload shows the away notice,
a different pun, two history entries, and record L2. 247 backend +
142 frontend tests.

## Intentionally deferred, and why

- **History caps at five entries in the UI** (the API returns all).
  The section scrolls; five is plenty of shame.
- **No leaderboard across attendees.** Still one query away
  (games grouped by workspace); still not asked for.
- **Banter pools are small (4-5 lines each).** Adding lines is a
  one-file edit in gameBanter.ts; the rotation handles any pool size.

## Known issues / tech debt

- The localStorage active-game marker is per browser. Playing the
  same workspace from two browsers means the second one may show the
  away notice for a game the first one watched die. Harmless, mildly
  chatty.
- `expired_while_away` from the server is still one-shot and still
  StrictMode-vulnerable on its own; it works in prod builds and as a
  secondary trigger. The localStorage path is the reliable one in dev.
- The away banter always draws from the loss pool, so after exactly
  N games the away pun equals the Nth rotation line. Nobody will
  notice, but now it is written down.

## What the next phase should tackle first

Unchanged from phase 27: a real rehearsal against api.openai.com.
Now with one more reason: model latency eats a clock that players
can now see running out.

## Gotchas

- StrictMode double-mount consumed the one-shot server flag. Any
  future "server tells the client exactly once" design will hit the
  same wall; either make the client idempotent (what we did) or gate
  the news client-side.
- DatasetPanel's open state is component state, not localStorage.
  Collapsing the whole Dataset *section* unmounts the panel and
  resets the open tabs. Deliberate: per-shape persistence across
  section toggles was not worth a second storage key.
- testing-library's getByText cannot match text split across the
  pre's JSON lines with a plain string; the tests use function
  matchers (`(text) => text.includes(...)`).
- The banter counter reseeds in applyGameStatus. If you add a call
  site that drops several puns between status applies, they rotate
  fine; the reseed only realigns the sequence at game boundaries.
