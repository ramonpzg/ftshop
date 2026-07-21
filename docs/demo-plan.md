# Demo plan

The run of show for the EuroSciPy 2026 session. Narrative and topics
live in [session-plan.md](session-plan.md), and the deck's slide-level
decisions live in [../deck/PLAN_V2.md](../deck/PLAN_V2.md); this file
is the operational walkthrough: every transition, button, hard stop,
cut, and fallback in one place. Advertised length 90 minutes; the core
below is 70, the remaining 20 are controlled flex (join dead air,
questions, recovery, the optional coda).

Room assumptions: up to 40 attendees, venue wi-fi that drops after idle
minutes and may demand a captive-portal login. Everything the session
depends on runs on the presenter's machine from reviewed local
fixtures. No attendee needs a provider account or API key.

The room model policy, enforced by the backend with 403s rather than
by hiding buttons: attendees play the room's default opponent
(configure a local Gemma endpoint as the default for the full room);
non-default opponent picks, position assessments (each one a
scenario-model call), and every generation job (image, video, audio
including local synthesis, live benchmarks) run only from the
presenter's machine. Scenario generation is also manual now, never
fired automatically per model turn, so one exchange costs the room
zero scenario calls instead of forty. The trustworthy client address
is the last X-Forwarded-For hop; the proxies overwrite anything a
client supplies.

## Before the room fills up

```
just reset-db
just seed
just start
just deck        # second terminal, port 3030
```

Open http://localhost:5173/?presenter=1 and join as yourself. The
`?presenter=1` flag shows the presenter panel and exempts your client
from the editing lock and remote camera moves. It is a convenience
flag, not auth; anyone who knows it gets the panel too. The budget is
protected one layer down: paid generation is loopback-only at the
backend, so a curious attendee with the flag can see buttons but
cannot spend money.

Attendees use the Network URL vite prints on startup (your LAN IP,
port 5173), without the flag. Write it somewhere visible.

Prep checklist, in order, on the actual laptop:

1. Throwaway move on the chess-machine page: backend is live.
2. Open the adaptation panel (left of the workspace grid on the
   chess-machine page). Confirm the scripted-illustration banner is
   visible; segment 6 opens by reading it out loud. Train the adapter
   on the reference snapshot, then run base and adapted benchmarks
   (replayed). Compare must show its table: legality 7/12 to 12/12,
   JSON validity 10/12 to 12/12, explanation rate 8/12 to 0/12
   regressed. Segment 6 re-runs these steps live, and benchmark
   history is immutable, so the prep runs stay in the run list as
   extra evidence rather than being overwritten.
3. On each modality page, run "Show adaptation evidence" and "Reveal
   cached artifact" once: the image pair, both audio clips with
   waveforms, and both video takes with poster and frame strip must
   render and play from local files with no network. These are the
   board-side copies of the evidence behind the deck's A/B slides,
   and the coda uses them.
4. Deck on 3030 with presenter mode and speaker notes. Step through
   part 1 to the TUI slide: either the local recording plays or the
   named placeholder shows. Know which one you have before the room
   does; per PLAN_V2, a missing asset stays a labelled placeholder,
   never an invented substitute.
5. If OPPONENT_MODELS/keys are set, start one throwaway game to see
   the model answer; if not, the fallback plan below covers it. For
   the full room, point OPENAI_BASE_URL at the llama.cpp endpoint
   serving the local Gemma: the default is what every attendee plays.
   The backend fails closed on this, twice over. Attendee game starts
   and model replies are refused unless the opponent endpoint is known
   local (a loopback OPENAI_BASE_URL, or OPPONENT_ENDPOINT_IS_LOCAL=1
   when the local endpoint runs on another LAN box) AND
   ROOM_MODEL_PLAY=1 is set. Set that flag only after the real load
   test below passed on this laptop: locality protects the budget,
   not capacity, and a half-configured room refuses games instead of
   routing forty browsers to a hosted model or piling them onto one
   llama.cpp queue. Without the flag the room free-plays and Gemma is
   presenter-led (segment 5 has both modes).
   Know the limit: every picker entry resolves against that one base
   URL and key. Offering the local Gemma default and a hosted Luna in
   the same picker needs per-model endpoints, which is the phase 4b
   named-profile registry; until that integration lands, run one
   endpoint at a time and treat the frontier beat as a
   presenter-machine reconfiguration, not a picker click. If the
   live-benchmark beat is planned, rehearse "Run base live" the week
   before, not
   while the room fills: the whole run has a deadline (60 s default,
   `BENCHMARK_RUN_DEADLINE_SECONDS` to change it) and a "Stop
   waiting" that stops the browser's wait (the server run continues
   to its deadline; live controls stay locked until it lands), so the
   worst case on stage is bounded, but the first try should not be in
   front of people. A live run only compares when the endpoint serves
   the adapter's own base model (the serving alias); a frontier model
   answering produces its own run and an honest "different models"
   refusal in Compare.
6. `just session-notebook` once, then close it: JupyterLab starts cold
   in seconds when segment 7 arrives.

Presenter controls (top of the board with `?presenter=1`): Lock
editing, Unlock editing, Bring everyone to presenter view, Send users
to their workspace, Prev/Next slide while presenting, Reset page, and
the Games room monitor with the two dataset export buttons (Download
SFT dataset, Download all shapes). Presenter actions reach attendee
browsers within a few seconds. Adaptation-panel controls render only
for the presenter client; attendees see the evidence read-only.

The week before: two load tests on the actual laptop, and time this
whole run of show once for real. First `just mock-llm` with the
backend pointed at it and `just load-test 40`: proves the backend
itself (moves, dataset writes, polling) holds under the room. Then
the one that decides segment 5's mode: point the backend at the real
llama.cpp Gemma endpoint and run `just load-test 40` again. Read the
"POST model-move" row of the latency report. If p95 sits inside
MODEL_TURN_DEADLINE_SECONDS (30 s default) with the error column at
zero, record the numbers and set ROOM_MODEL_PLAY=1 for the workshop:
the room plays Gemma directly. If it does not, leave the flag unset
and run segment 5 in its free-play mode; do not shorten the deadline
or thin the room to force a pass. The mock run says nothing about
inference capacity; only the real run does.

## Run of show

Each segment lists: target duration and the hard stop, what the room
predicts before the action, what participants do, the one artifact
everyone inspects, the sentence that closes the loop, the cut when
late, and the fallback when something fails.

### 1. Where this came from, ending in the TUI (deck part 1) - 9 min, hard stop at 0:09

- Predict: nothing yet; state the board URL twice while people settle.
  Joining waits until segment 4; the deck needs no login.
- Participants: none; this is origin, not instruction. No chess is
  explained yet.
- Artifact: the TUI recording, phone-shaped and readable from the
  back: local llama.cpp starts, one participant move, one Gemma move,
  the dry commentary, the game record, a short replay. The origin
  beats land on the way there: the book opened five times, Duolingo
  chess found in Japan, Oscar, 5 then 20 games a day then 500 in the
  first month, the Queen's Gambit finally watched, the Sydney flight
  where the opponent vanished with the connection. The dog-thinking
  meme and "what could possibly go wrong" stay.
- Close the loop: one object already contains the whole workshop:
  local model, real rules, recorded evidence, and a personal
  objective (win while taking as few opposing pieces as possible).
- Cut: compress the origin slides to the flight and the meme; the TUI
  recording is never cut.
- Fallback: the recording is a local file with a poster frame. The
  phone itself stays in the pocket unless chosen. If the recording is
  still a placeholder, narrate over the placeholder geometry and lean
  on segment 5, where the room plays the same loop themselves.

### 2. Four adaptation problems, which one was adapted (deck part 2) - 8 min, hard stop at 0:17

- Predict: per modality, which of the two outputs came from the
  adapted model. Collect shouted votes; if the room is quiet, reveal
  each answer immediately and keep moving, per PLAN_V2.
- Participants: voting out loud; nothing to click.
- Artifact: the reveal table, one row per modality: the answer, the
  exact target behavior, one metric with sample size, cached-or-live
  provenance, and one limitation or regression. At least one row
  improves its target and gets worse somewhere else.
- Along the way: text does more than choose a move; the real-world
  mappings are Luna's work and are labelled scenario writer, never a
  fine-tuned chess model. The video stages the mapped situation and
  contains no board, pieces, or notation.
- Close the loop: fine-tuning is a trade, not a ceremony where every
  score rises. The board will prove this again with hashes in
  segment 6.
- Cut: three real-world mappings down to one; the A/B slides and the
  reveal table stay.
- Fallback: every pinned output is a local file; a provider request
  is an optional live replacement, never the only thing the room can
  see.

### 3. Why adapt anything (deck part 3) - 5 min, hard stop at 0:22

- Predict: for the last model problem they personally hit, which
  intervention it actually needed.
- Participants: none; this is the argument.
- Artifact: economics at a target quality, one row per modality, task
  and threshold stated, `[SOURCE, DATE]` placeholders until checked;
  the data circles ending in the train/eval split; the style beats by
  name (goth Minions, the corporate-lamp paragraph, the cookie GIF)
  landing on the concrete Canva case; then the decision slide.
- Close the loop: prompt, retrieve, use tools, or fine-tune. Choose
  the intervention, not a tribe, and keep the options.
- Cut: the future model tree first, then the style beats down to
  Canva alone. The decision slide is never cut.
- Fallback: none needed; slides are local.

### 4. The chess objects, after we have seen them (deck part 4) - 3 min, hard stop at 0:25

- Predict: what FEN has to encode for a legal-move list to be
  derivable from it.
- Participants: join the board with their name now; say the Network
  URL again and leave it on screen. Joins land while the recap runs,
  and segment 5's start absorbs stragglers.
- Artifact: one board, four representations of the same actual move
  (FEN stores the position, UCI names it for machines, SAN for
  people, PGN stores the history), and the one-job slide: model
  proposes, python-chess validates, Stockfish optionally evaluates.
- Close the loop: the recap names the objects the room already
  watched in the TUI. En passant lives in the notebook unless someone
  asks.
- Cut: the notation morph alone carries the segment.
- Fallback: if the venue wi-fi blocks joining, continue
  presenter-only and say so; every board segment has a presenter-led
  mode.

### 5. The shared game (board) - 15 min, hard stop at 0:40

Switch to the board. Send users to their workspace. Unlock editing.

This segment has two room modes, decided the week before by the real
load test, never on the day. Locality is not capacity: forty
simultaneous requests queue behind one llama.cpp server and exhaust
the 30-second model-turn deadlines even though every call is free.
The backend enforces the choice: attendee timed games and model
replies are refused unless ROOM_MODEL_PLAY=1 is set, and that flag is
set only after the recorded load test passed. Attendee panels show
"Free play today" instead of a Start button when the room is closed.

- Predict: whether the small local model will beat them; whether their
  own moves are all legal.
- Participants, opened room (load test passed, ROOM_MODEL_PLAY=1):
  hands-on. Double-click their workspace, Start game (five minutes),
  play the configured model. Open one dataset tab before moving and
  leave it open: the newest row replaces the old one in place. That is
  the aha; do not rush it.
- Participants, closed room (the default): free play. Pair with a
  neighbor on one board or play both sides; every legal and illegal
  move lands in the same dataset tab with the same replace-in-place
  aha and the same reward -1 lesson. Model inference happens once,
  presenter-led on the projector: the presenter starts the timed game
  and the room watches Gemma answer, then everyone reads their own
  rows. The data story is identical; only who the opponent is changes.
- Artifact: their own dataset rows, plus one illegal-move attempt on
  purpose: board unchanged, reward -1. If the model answers garbage,
  celebrate: the failed attempt lands in model_attempts, the turn
  retries, and after the budget a labelled fallback move plays. Run
  the two text jobs (prompt eval, reward eval) and read the live
  numbers next to the cached ones (the eval rows open into
  definitions and provenance).
- The two-game beat when OPPONENT_MODELS is set: the room plays the
  small default model; the presenter plays the frontier model once on
  the projector (non-default opponents are presenter-only by policy).
  Same recipe, same board, different results, seen side by side. Both
  entries resolve against the one configured endpoint, so this beat
  needs a single endpoint that serves both models (OpenRouter does);
  splitting it across local llama.cpp and a hosted API waits on the
  phase 4b named-profile registry, and until then the frontier beat
  on a local-endpoint day is a presenter-machine reconfiguration
  between games.
- Scenario beat, presenter-run: Assess position on a mid-game moment
  from the presenter's own workspace; the room reviews, accepts, or
  edits mappings that land in their own. One scenario call per beat,
  not one per exchange per attendee. Keep Ramon's aside: rage-quitting
  against the bot is a labeled data point now.
- Close the loop: pairs in. Everything they just made is the left side
  of the recipe.
- Cut: one game instead of two; skip the scenario beat (segment 6's
  freeze still shows raw/approved counts from rehearsal data).
- Fallback: no key or provider down means Start game reports the model
  unavailable with a retry button; play a free-play game against a
  volunteer instead and narrate the same dataset rows. The mock LLM
  (`just mock-llm`) is the rehearsal stand-in, not a live-room tool.

### 6. The adaptation evidence chain (board) - 13 min, hard stop 0:53

Bring everyone to presenter view. Adaptation panel, top to bottom.
Open by reading the banner out loud: this chain is a scripted
illustration, no model was trained; training and replayed benchmarks
replay authored fixtures, and only a live base run calls a real model.
The chain earns trust by narrating exactly what it is.

- Predict: what a training run needs to be reproducible. Collect three
  answers before opening the panel.
- Participants: watching; two called-out checks (do the hashes match
  between adapter card and snapshot card; which metric regressed).
- Artifacts, one per step:
  1. Freeze room dataset: the new snapshot card with eligible versus
     excluded counts, scenario raw/approved, and its content hash.
  2. Config card: LoRA parameters, seed, output task (the sft-v2
     contract), config hash, and the three Gemma roles behind the
     disclosure.
  3. Train adapter on the reference snapshot: adapter card marked as
     a scripted replay, result source cached. Then select the
     just-frozen room snapshot and train again: read the 409 out
     loud. The scripted result is bound to the reference hash and
     will not pose as training on the room's data. That refusal is
     the honesty model.
  4. Run base and adapted benchmarks; the run badges say "replayed
     (scripted)". Optionally, with a local endpoint serving the base
     model, Run base live: the run list shows live provenance with a
     non-null checkpoint. The whole run is bounded (60 s deadline,
     three consecutive transport failures abort it, "Stop waiting"
     stops the browser's wait while the server run finishes to its
     deadline and live controls stay locked until it lands), so a
     hung provider costs a minute of stage time, not the segment. If
     a call fails, that run's position set differs and Compare says
     Not comparable per metric; if the endpoint serves some other
     model, Compare refuses with "different models" instead of
     pretending a Luna run is the Gemma before. Do not fish for
     either; read them out when they happen.
  5. Compare: deltas with verdict words, the regression on screen,
     one example opened: the scripted base reply fills the optional
     "why" field, the scripted adapted reply is bare JSON. Legality
     7/12 to 12/12, JSON validity up, explanation rate 8/12 to 0/12.
     The replies are authored, so say what the chain actually shows:
     this is how the trade a bare-completion training set makes would
     be measured, optional chatter collapsing while format and
     legality rise. The measurement is real; the model run is not.
- Close the loop: adapter out, eval always. Every link is
  content-addressed: the adapter names its dataset hash, the delta
  names its frozen suite. Break either link and the panel says Not
  comparable instead of inventing a number.
- Cut: skip the live base run and the refusal beat; keep freeze,
  train, compare.
- Fallback: everything here is fixture-backed and keyless by design.
  The live button exists only when credentials do, and the backend
  refuses paid runs from any machine but the presenter's.

### 7. Notebook practice (standalone Jupyter) - 14 min, hard stop 1:07

The deliberate switch: `just session-notebook` opens JupyterLab in its
own window. The board stays up but the projector follows the notebook.

- Predict: how many lines the minimal SFT run needs.
- Participants: hands-on for anyone with a laptop; everyone else
  follows the projector. Export the room's dataset first (presenter
  panel, Download SFT dataset) and note the path
  `data/processed/text/chess_sft.jsonl`; the notebook loads exactly
  that file.
- Artifact: the notebook's dataset-to-training walkthrough over the
  room's own rows.
- Close the loop: the notebook is the take-home; the whiteboard was
  the evidence; the deck was the story.
- Cut: walk two cells instead of the full arc; the notebook is
  self-serve after the session.
- Fallback: the notebook's provider and local-model cells are optional
  and clearly marked; skip them keyless. If JupyterLab will not start,
  the mini IDE snippets on the board cover the same training code
  shapes.

### 8. Close (notebook, then the room) - 3 min, hard stop 1:10

- Restate the four outcomes as questions; let the room answer.
- Repo link and resources from the notebook's final section (the deck
  is not reopened for this).
- The economics point, briefly: open models keep matching what closed
  models did months ago, the barrier keeps falling, owning an adapted
  model is a real option among the four interventions.

### Optional coda: what the room produced (board) - 2 min, from flex

When time allows, end on the board instead of the notebook: the
room's own games, dataset rows, and frozen snapshot on screen. A
result, not another explanation. Whether the session finishes here or
in the notebook is a rehearsal decision, per PLAN_V2.

Core total: 70 minutes at the hard stops. The remaining 20 absorb
joins, questions, failures, and the coda; if nothing goes wrong,
segments 5 and 7 stretch to fill. The deck's part 5 (technical
reference) is modular and unscheduled: it exists for questions and
spare time, and it is the first thing that never happens.

## If something goes wrong mid-session

- Whiteboard fails outright: per PLAN_V2, stay in the deck long enough
  to show the pinned model outputs through its components, then jump
  directly to the notebook. Do not spend ten minutes repairing
  collaboration in front of the room.
- Board frozen / weird state for one attendee: they reload; identity
  and workspace persist (localStorage + backend), the workspace shape
  re-materializes, and the camera returns to it.
- Whole page feels off: **Reset page** on chess-machine clears every
  workspace's game state without restarting anything. Benchmark runs,
  adapters, and snapshots survive; they are room-level evidence, not
  page state.
- Need a truly clean slate: `just reset-db && just seed` (attendees
  rejoin; full workshop-state wipe, canvas untouched). Frozen room
  snapshots are lost; the reference chain reseeds.
- Deck damaged mid-session: attendees cannot delete or restructure
  authored content; only the presenter can. If it happens, stop the
  whole stack including the sync server, copy
  `data/canvas/snapshot.prev.json` over `snapshot.json`, start again.
  The room holds the document in memory, so restoring the file while
  the sync server runs would just get overwritten.
- Provider trouble: the model-turn fallback and retry button handle a
  flaky endpoint; a dead endpoint turns segment 5 into free play plus
  narration and removes only the optional live-benchmark beat from
  segment 6. A hung live benchmark ends itself at the run deadline;
  Stop waiting frees the browser sooner while the server run finishes
  on its own. Nothing else in the core touches a provider.
- App unusable entirely: `just session-notebook` opens the standalone
  notebook and the session continues from segment 7's material; the
  committed media under `artifacts/cached/media/` can be opened
  directly from the filesystem if a reveal is needed.

## Timing evidence

Rule: time the walkthrough on the real laptop, do not estimate it from
headings. Record the measured core duration, what was skipped, and
every wait on the system. The phase-34 rehearsal measurements and the
current cut list live in
[notes/ai/phase-34-learning-experience.md](../notes/ai/phase-34-learning-experience.md);
re-measure after any structural change to this file.
