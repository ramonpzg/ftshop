# Demo plan

For running the EuroSciPy 2026 session with this app. 90 minutes,
one shared chess domain, four modalities. The narrative and topic plan
for the session itself lives in [session-plan.md](session-plan.md);
this file is the app walkthrough.

The current timing and detail-first order describe the existing build. The
accepted direction for phase 34 is a compact motivation and chess grounding,
then outcome-first demos across all four modalities, followed by technical
decomposition. Keep this runbook operational until that revised flow has been
implemented and rehearsed.

## Before the room fills up

```
just reset-db
just seed
just start
```

Open http://localhost:5173/?presenter=1 and join as yourself. The
`?presenter=1` flag shows the presenter panel and exempts your client
from the editing lock and remote camera moves. It is a convenience
flag, not auth; anyone who knows it gets the panel too.

Attendees use the Network URL vite prints on startup (your LAN IP,
port 5173), without the flag. Write it somewhere visible. Do a
throwaway move on the chess-machine page to confirm the backend is
live before anyone else joins.

Presenter actions reach attendee browsers within a few seconds; each
client polls presenter state. Lock editing makes attendee canvases
read-only. Bring everyone to presenter view pulls their cameras to the
exact region you are looking at, and Prev / Next keeps them on your
slide frame while presenter mode is active. Someone joining late lands
on your current view, not a blank page. Send users to their workspace
releases their cameras and returns each to their own board.

The presenter panel's Games section is your room monitor: who is
playing, how much clock they have, who finished and how. When the
first round wraps, **Download all shapes** collects every sample from
every game into one JSONL for the training demo; **Download SFT
dataset** is the prompt/completion subset the snippets load. One
click each, no shell.

Start the deck too: `just deck` (port 3030). The Presentation page
embeds it; the Open link on that panel gives you the deck in its own
tab with presenter mode and speaker notes. The LiveRoom slide talks to
the backend through the deck's own /api proxy, so it works from port
3030 and from any attendee machine that can reach yours. Backend down
shows a terse offline hint; a drop mid-talk keeps the last numbers
visible with a reconnecting note. Attendees viewing the embedded deck
panel get your machine's address automatically when the stored URL
points at localhost.

The week before: run the load test once on the actual laptop
(`just mock-llm`, backend pointed at it, `just load-test 40`). It
simulates a full room and prints latency percentiles; see
local-dev.md for the three commands.

## Flow

### 1. Presentation (5 min)

Land here by default. The page carries an eleven-frame slide deck
seeded from the session plan; fill the frames with your content and
assets before the session. Use the Prev / Next controls (bottom right)
or PageUp / PageDown from a clicker to step through frames. Everything
you author lives in the shared room and persists through the backend
as you edit; the badge top left should read "Room: live".

Tell attendees to open the app and enter their name now, so workspace
creation isn't blocking the room later.

### 2. Building a Chess Machine, text (35 min)

The main technical section. Each attendee's join creates their
workspace here automatically.

- Walk the seeded notes: prompt templates, chess datasets, SFT, LoRA
  and QLoRA, RL environments, Stockfish, legality checking, evals.
- Have attendees double-click into their own workspace and play a
  couple of moves. Point at the dataset panel updating live. This is
  the PGN-prefix, FEN-to-move, FEN+legal-moves, board-tensor, and
  policy/value rows building from *their* game, not a canned example.
- Click **Start game**: a timed match from the starting position (five
  minutes by default, up to thirty in the picker). The configured model
  answers every move, its moves feed the same dataset rows, and the
  Analysis section refreshes after each exchange with a position read
  plus the real-world scenario mapping. If the model picks an illegal
  move, celebrate: the environment caught it, reward -1, that is the
  RL slide happening live.
- The two-game beat: with OPPONENT_MODELS set (see local-dev.md), the
  model picker sits next to the clock. Play one five-minute game
  against the configured small model, then the configured frontier
  model. Same recipe, same board, visibly different results. Let the
  room feel the gap before you show the fine-tuning that closes it.
- Point at the clock and the **Start over** button. Quitting a match
  costs a loss, and so does the flag falling; the W/L/D record and
  the match log under the board keep score. Say it out loud:
  rage-quitting against the bot is a labeled data point now.
  Checkmates end the game on their own, either direction, and every
  check, mate, and loss comes with a rotating one-liner.
- Open one of the dataset tabs before playing. It stays open while
  moves land, so the room watches the newest row replace the old one
  in place. That is the aha moment; do not rush past it.
- Click **Export dataset**: the room's games become
  `data/processed/text/chess_sft.jsonl`. The standalone Jupyter
  notebook and the Unsloth and Axolotl snippets in the mini IDE can
  load that exact path. Do not switch to Jupyter here unless the
  accepted run of show explicitly calls for it.
- Open the mini IDE. Walk through the snippets: the prompt template,
  the chat template, the legal-move validator, the dataset row builder,
  the reward function, and the LoRA training run. These are real code.
  The reward function in the IDE is the literal function the backend
  runs.
- Attempt an illegal move on screen. The board doesn't change and the
  move status shows reward -1. That is what "the environment can
  validate every move" means for RL.
- Run both text jobs from the config panel (prompt eval, reward eval).
  Point out the eval panel now shows live numbers (legal move rate,
  valid JSON rate) next to the cached illustrative ones (centipawn
  loss, mate-in-one accuracy, explanation correctness), and explain
  why those specific three are cached: they need Stockfish or a judge
  model, which is out of scope for a workshop backend.

If you want everyone looking at the same thing: **Bring everyone to
presenter view**, narrate, then **Send users to their workspace** to
let them resume. **Lock editing** during a narrated segment if boards
are distracting; **Unlock editing** to hand control back.

### 3. Painting Our Pieces, image (15 min)

Switch pages. Walk the seeded content: image-caption pairs, trigger
words, aspect ratios, captions.

Open the modality panel. Run "Show dataset", a small cached batch of
piece image/caption pairs using the real Cburnett piece SVGs.
"Reveal cached artifact" shows a before/after style-transfer example.
Point at the eval panel: piece identity, style consistency, prompt
adherence, caption sensitivity, human preference, all cached, all
labeled as such.

With FAL_KEY set, type a prompt in the generate block and hit
Generate: FLUX.2 Klein 4B renders it in a few seconds, swap the picker
to schnell to compare. The result downloads to the backend, so it
stays after fal's URL expires. Have attendees draw their favourite
piece with the draw tool first, then generate the styled version from
their caption. That is the page's whole argument in one beat.

### 4. Giving the Board Sound, audio (15 min)

Same pattern. Run "Make spectrogram", this one's a real (if toy)
calculation, not a fixture: it deterministically turns a duration and
a tag list into a spectrogram-shaped grid, rendered live in the
artifact panel. "Reveal cached artifact" shows the illustrative capture
sound example. Eval panel: tag similarity, duration error, clipping,
event recognisability, human preference.

With `just install-audio` done, generate a capture sound with
musicgen-small running on your own machine, then swap the picker to
stable-audio-open for the diffusion take on the same prompt. The
standalone Jupyter notebook also contains the click synthesis and
spectrogram material, but it is a separate presenter asset rather than
an embedded panel.

### 5. Video of the Real-World Use Case, video (15 min)

Same pattern again, so the parallel across all four modalities is
obvious by now. Run "Sample frames", another real calculation,
uniform frame sampling over a virtual clip length. "Reveal cached
artifact" shows the knight-fork clip example. Eval panel: action
success, piece identity consistency, temporal flicker, caption
adherence, human preference.

Generate is wired to LTX 2.3 fast (about a minute for six seconds,
keep talking; the panel says so) with Veo 3.1 fast in the picker for
the frontier comparison. Costs are real here: cents per second, not
fractions of a cent per image. Say that out loud, it is the lesson.

### Wrap-up (5 min)

Back to Presentation. If you played moves during setup or rehearsal,
**Reset page** on chess-machine clears everyone's game state cleanly
before Q&A or a second run.

## If something goes wrong mid-session

- Board frozen / weird state for one attendee: they can reload, their
  identity and workspace persist (localStorage + backend), and the
  app re-materializes their workspace shape and returns the camera to
  it automatically.
- Whole page feels off: **Reset page** clears every workspace's game
  on chess-machine without restarting anything.
- Need a truly clean slate: `just reset-db && just seed` on the
  backend (attendees will need to rejoin, that's a full data wipe,
  not a per-page reset). Your authored slides are untouched: the canvas
  lives in `data/canvas/snapshot.json`, not in the database.
- Deck damaged mid-session: attendees cannot delete or restructure
  your authored content (ownership rules block it in their clients),
  so this now takes the presenter doing it. If it happens, stop the
  whole stack including the sync server, copy
  `data/canvas/snapshot.prev.json` over `snapshot.json`, start again.
  The room holds the document in memory, so restoring the file while
  the sync server runs would just get overwritten.
- App unusable or the network is unavailable: `just session-notebook`
  opens `notebooks/full-session.ipynb` in JupyterLab. It is a separate
  pragmatic asset, not an iframe. Optional live cells still depend on
  their configured credentials and packages, so rehearse the exact
  fallback path before relying on it.
