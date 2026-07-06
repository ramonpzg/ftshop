# Demo plan

For running the EuroSciPy 2026 session with this app. 90 minutes,
one shared chess domain, four modalities. The narrative and topic plan
for the session itself lives in [session-plan.md](session-plan.md);
this file is the app walkthrough.

## Before the room fills up

```
just reset-db
just seed
just start
```

Open http://localhost:5173, join as yourself (e.g. "Presenter"). Do a
throwaway move on the chess-machine page to confirm the backend is
live before anyone else joins.

## Flow

### 1. Presentation (5 min)

Land here by default. The page carries an eleven-frame slide deck
seeded from the session plan; fill the frames with your content and
assets before the session. Use the Prev / Next controls (bottom right)
or PageUp / PageDown from a clicker to step through frames. Everything
you author is saved to the backend as you edit; the badge top left
should read "Canvas: saved".

Tell attendees to open the app and enter their name now, so workspace
creation isn't blocking the room later.

### 2. Building a Chess Machine — text (35 min)

The main technical section. Each attendee's join creates their
workspace here automatically.

- Walk the seeded notes: prompt templates, chess datasets, SFT, LoRA
  and QLoRA, RL environments, Stockfish, legality checking, evals.
- Have attendees double-click into their own workspace and play a
  couple of moves. Point at the dataset panel updating live — this is
  the PGN-prefix, FEN-to-move, FEN+legal-moves, board-tensor, and
  policy/value rows building from *their* game, not a canned example.
- Open the mini IDE. Walk through all four snippets: the prompt
  template, the legal-move validator, the dataset row builder, and the
  reward function. These are real code — the reward function in the
  IDE is the literal function the backend runs.
- Attempt an illegal move on screen. Show it gets rejected and the
  board doesn't change — this is what "the environment can validate
  every move" means for RL.
- Run both text jobs from the config panel (prompt eval, reward eval).
  Point out the eval panel now shows live numbers (legal move rate,
  valid JSON rate) next to the cached illustrative ones (centipawn
  loss, mate-in-one accuracy, explanation correctness) — and explain
  why those specific three are cached: they need Stockfish or a judge
  model, which is out of scope for a workshop backend.

If you want everyone looking at the same thing: **Bring everyone to
presenter view**, narrate, then **Send users to their workspace** to
let them resume. **Lock editing** during a narrated segment if boards
are distracting; **Unlock editing** to hand control back.

### 3. Painting Our Pieces — image (15 min)

Switch pages. Walk the seeded content: image-caption pairs, trigger
words, aspect ratios, captions.

Open the modality panel. Run "Show dataset" — a small cached batch of
piece image/caption pairs using the real Cburnett piece SVGs.
"Reveal cached artifact" shows a before/after style-transfer example.
Point at the eval panel: piece identity, style consistency, prompt
adherence, caption sensitivity, human preference — all cached, all
labeled as such.

### 4. Giving the Board Sound — audio (15 min)

Same pattern. Run "Make spectrogram" — this one's a real (if toy)
calculation, not a fixture: it deterministically turns a duration and
a tag list into a spectrogram-shaped grid, rendered live in the
artifact panel. "Reveal cached artifact" shows the illustrative capture
sound example. Eval panel: tag similarity, duration error, clipping,
event recognisability, human preference.

### 5. Video of the Real-World Use Case — video (15 min)

Same pattern again, so the parallel across all four modalities is
obvious by now. Run "Sample frames" — another real calculation,
uniform frame sampling over a virtual clip length. "Reveal cached
artifact" shows the knight-fork clip example. Eval panel: action
success, piece identity consistency, temporal flicker, caption
adherence, human preference.

### Wrap-up (5 min)

Back to Presentation. If you played moves during setup or rehearsal,
**Reset page** on chess-machine clears everyone's game state cleanly
before Q&A or a second run.

## If something goes wrong mid-session

- Board frozen / weird state for one attendee: they can reload — their
  identity and workspace persist (localStorage + backend), and the
  app re-materializes their workspace shape and returns the camera to
  it automatically.
- Whole page feels off: **Reset page** clears every workspace's game
  on chess-machine without restarting anything.
- Need a truly clean slate: `just reset-db && just seed` on the
  backend (attendees will need to rejoin — that's a full data wipe,
  not a per-page reset). Your authored slides are untouched: the canvas
  lives in `data/canvas/snapshot.json`, not in the database.
- Deck damaged mid-session (accidental mass delete): stop the server,
  copy `data/canvas/snapshot.prev.json` over `snapshot.json`, start
  again. That backup holds the state from just before the last save.
