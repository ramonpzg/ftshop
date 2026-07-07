# Learning guide: phase 28, four small fixes and one ambush by React

This phase came straight from using the app: a silent loss after a
server restart, dataset tabs that slammed shut mid-demo, no memory of
the matches played, and endings that deserved better writing. Small
fixes, but two of them are the kind that teach you something.

## The loss nobody mentioned

Phase 27's lazy expiry was correct and rude. Come back after a server
restart and your dead game had already been converted into a timeout
loss, accurately, silently. The record said L2 where you remembered
L1, and the app offered no explanation. Correct state, missing story.

The obvious fix: have the server flag the read that performed the
conversion. `expired_while_away: true`, one-shot, on exactly the
response that broke the news. Clean design. It failed immediately.

Here is the question this bug wants you to sit with: what happens to
a one-shot server message when React StrictMode mounts your component
twice? StrictMode, in development, mounts, unmounts, and remounts
every component to flush out effect bugs. The throwaway first mount
fetched the status, consumed the flag, and threw the answer away; the
real mount fetched again and got `false`. The server told the truth
exactly once, to a listener that no longer existed. Any protocol of
the form "the server says X exactly once" has this failure mode, and
not only under StrictMode: two tabs, a retry, a prefetch, anything
that reads twice.

The fix is to make the client capable of deducing the news instead of
needing to be told: localStorage remembers the id of the match this
browser was in. On mount, if that game is gone and the newest
finished game is a timeout, the story writes itself. The server flag
stays as a second trigger, but the deduction is idempotent: read the
status ten times and the conclusion is the same. That is the general
lesson. One-shot messages are fragile; derivable state is not.

## The tabs that would not stay open

You open "FEN -> move", play a move to show the room the new row, and
the tab snaps shut. The aha moment, cancelled. Why?

Look at what the old panel rendered: the last six dataset rows, each
a `<details>` element keyed by row id. A move creates six new rows,
so the six visible rows were six *different* rows with six different
keys. React saw new keys, unmounted everything, mounted fresh
elements, and fresh `<details>` elements are closed. The browser was
holding your open state in the DOM, and we kept discarding that DOM.

The fix inverts the data model to match what the panel was pretending
to be all along: one group per dataset shape, in teaching order,
keyed by shape name. Shape names are stable forever, so the elements
persist. Open state moved from the DOM into React state, and the
group shows the newest payload plus a count badge. Now the demo works
the way it should: open the tab once, play moves, and watch the
payload replace itself in place while the counter climbs. Ask
yourself where else a key choice is quietly deciding what state
survives a render. Keys are not an optimization hint; they are an
identity claim.

## The match log

The games table already knew everything; nothing displayed it. One
repo query (finished games, newest first, each with a correlated
subquery counting its legal moves) and one formatting function later,
the board section lists the last five: "Loss, time. 7 moves on a 5
min clock." Note what was *not* built: no new table, no endpoint of
its own, no pagination. The data was already durable because phase 27
put the game entity in the right place, and features that fall out of
prior good decisions are the cheapest features there are.

## Puns, deterministically

Every ending now comes with a one-liner: four pools in gameBanter.ts
for check, checkmate, win, and loss. "A loss is just a labeled
example. Label: ouch."

The engineering detail worth noticing is what is missing:
randomness. `pickBanter(kind, index)` walks the pool by index, the
component increments a counter per pun, and the counter reseeds from
games played on every status refresh. Why not Math.random()? Because
random is untestable, unreproducible, and happily repeats itself two
events in a row, which is the one thing a joke must not do. Rotation
guarantees consecutive lines differ, tests can assert exact strings,
and the seed means the pun after your third loss differs from the
pun after your second even across a reload. Comedy, like training,
benefits from a fixed seed.

One more small mercy went in nearby: a move that fails for any
reason other than the clock now says "That move never reached the
server. Is the backend running?" instead of doing nothing. Silence
is the worst error message, and it was the default.
