# Learning guide: where your slides actually live now

You asked for one thing above all: stop the server, come back
tomorrow, and everything is still there. This guide walks through how
that works, what else changed while we were in there, and the handful
of traps we stepped on so you don't have to.

## The deck used to live in your browser. Think about why that's bad.

Before this pass, the canvas persisted through tldraw's
`persistenceKey`, which means IndexedDB, which means browser storage.
Here's the question worth sitting with before reading on: IndexedDB is
keyed by *origin*. You author your slides at `http://localhost:5173`.
At the venue you serve the app on your LAN IP so attendees can reach
it, and you open `http://192.168.1.7:5173` yourself. What do you see?

A blank canvas with the starter notes. Different origin, different
IndexedDB, different universe. Your deck is still on your laptop, in a
database keyed to a hostname you're no longer using, and no amount of
frantic clicking at the podium will move it over. Same story if you
switch browsers, reinstall, or let Safari decide your data was getting
stale, which it does after seven days, because Safari loves you.

So the fix is almost boring: the document is a file. The backend owns
`data/canvas/snapshot.json`, the frontend fetches it on mount, loads
it into a store it builds itself, and saves back on every change.
Files you can commit. Your slide deck is now something `git diff` can
see, which is a sentence that should make you slightly happy.

Why a file and not a row in SQLite, when SQLite is right there,
holding everything else? Because of a command you will type at the
worst possible moment: `just reset-db`. It wipes workshop state,
users, moves, workspaces, between rehearsals. If the deck lived in the
same database, the command that resets attendee chess games would also
eat three evenings of slide work. Separate failure domains: `reset-db`
touches the database, `reset-canvas` touches the deck, and neither can
hurt the other. There's also `snapshot.prev.json`, a one-step backup
written before every overwrite, for the day you select-all-delete and
the save loop faithfully persists your mistake.

## The save loop, or: how not to lose edits politely

Every document change marks the store dirty; a scheduler waits 800ms
of quiet, then PUTs the snapshot. One save in flight at a time, and
edits made mid-save queue exactly one follow-up. If the backend is
down, the scheduler keeps the dirty flag and retries on a timer, and
the badge top-left flips to "Canvas: save failed" so at least you die
informed.

One decision here deserves a Socratic pause. When the app boots and
the snapshot fetch *fails*, the canvas refuses to mount at all. That
seems rude. Why not show a fresh canvas and let you work? Trace it:
fresh canvas means the seeder runs, which creates pages, which marks
the document dirty, which, the moment the backend comes back, saves a
nearly empty document over your real one. The refusal is the feature.
A blank screen is recoverable; a clobbered snapshot is a bad morning.

## tldraw 5 and the trap we walked into for you

The upgrade from tldraw 3 to 5 was smaller than two major versions
suggest: custom shapes now register their prop types through a module
augmentation (which finally makes `createShapes` type-check them),
selection indicators became `Path2D` objects instead of JSX, and
that's most of it.

The trap: when you create your own store with `createTLStore`, tldraw
does *not* merge in the default shape utilities the way the `<Tldraw>`
component does. Pass only your custom shapes and the store schema has
no idea what an arrow is, so it dies at startup with a migration error
that mentions arrows and bindings and nothing about what you actually
did wrong. The fix is one spread:

```ts
createTLStore({
  shapeUtils: [...defaultShapeUtils, WorkspaceShapeUtil, ModalityPanelShapeUtil],
  bindingUtils: defaultBindingUtils,
  assets: backendAssetStore,
})
```

While we were in there, fonts and icons moved from tldraw's CDN into
the bundle via `@tldraw/assets`. Question: why does a workshop app
care where its fonts come from? Answer: because the venue wi-fi will
be bad, that's not a risk assessment, it's a law of nature, and an app
that needs a CDN to draw its own toolbar is an app with a hidden
dependency on someone else's uptime. Everything is local now. If your
laptop boots, the app runs.

## Two races and the one-statement cure

The review caught something you'd only see live on stage: thirty
people join at once, and six of them land on the same spot on the
canvas, workspaces stacked like a pile-up. The old code did this:

```python
position_index = count_workspaces_for_page(conn, page_id)  # everyone reads 4
insert_workspace(..., position_index)                       # everyone writes 4
```

Read, then write, with a gap in between. Every request that reads
before the first one writes gets the same count. The cure is to stop
having a gap:

```sql
INSERT INTO workspaces (..., position_index, ...)
VALUES (..., (SELECT COUNT(*) FROM workspaces WHERE page_id = ?), ...)
```

One statement, and SQLite executes a statement atomically under its
write lock. There is nowhere for a second request to sneak in. The
same trick now allocates move numbers. Worth asking yourself: why is
this fine for SQLite when the textbook answer is "use a transaction"?
Because a single statement *is* the transaction, and the fanciest
concurrency tool is the one you don't have to remember to use.

## Making the presenter buttons mean something

"Bring everyone to presenter view" used to move exactly one camera:
yours. The state changed in the database, and no other client ever
asked about it. Now every client polls presenter state every three
seconds. Lock lands as actual tldraw read-only on attendee canvases,
never on yours, you're exempt, along with camera moves, because your
client carries `?presenter=1`. That flag also gates the panel itself,
since the previous arrangement gave every attendee a working "reset
everyone's game" button, which is less a presenter tool than a dare.

One subtlety worth noticing: on the very first poll, the client
applies the lock but not the camera move. Why? Because "the state says
presenter mode" and "the presenter just pressed the button" are
different facts. A latecomer joining mid-lecture should not have their
camera yanked by a button pressed four minutes ago; they get moved on
the next actual change. The poll compares `updated_at` timestamps to
tell the difference.

## The board teaches the reward function now

Try an illegal move. The board used to reject it silently, which was
correct and useless. Now it prints `Illegal: e2e5. Reward -1` under
the board in red. That's the RL lesson wearing a status line: the
environment validates every action and prices it. Legal move, +1.
Check, +2. Mate, +10. Blunder into an illegal move on stage and you're
not fumbling, you're demonstrating the reward function. You're
welcome.

The mini IDE picked up two snippets to close the loop: the Jinja chat
template (the thing the tokenizer actually renders, and the thing that
silently ruins fine-tunes when it doesn't match the model family) and
a real TRL `SFTTrainer` run with a `LoraConfig`, pointed at exactly
the FEN-to-move rows the board generates. The pipeline on screen is
the pipeline in the slides.

## What to poke at next

Open two browsers, one with the presenter flag, one without. Lock
editing and try to drag a note in the attendee window. Then stop the
backend mid-edit, watch the badge complain, restart it, and watch the
edit arrive anyway. Then look at `data/canvas/snapshot.json` in a
diff. It's your deck, as data, in your repo, which is where it should
have been all along.
