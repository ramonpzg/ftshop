# Demo plan

The run of show for the EuroSciPy 2026 session. Narrative and topics
live in [session-plan.md](session-plan.md); this file is the operational
walkthrough: every transition, button, hard stop, cut, and fallback in
one place. Advertised length 90 minutes; the core below is 72, the
remaining 18 are controlled flex (join dead air, questions, recovery,
optional stretches).

Room assumptions: up to 40 attendees, venue wi-fi that drops after idle
minutes and may demand a captive-portal login. Everything the session
depends on runs on the presenter's machine from reviewed local
fixtures. No attendee needs a provider account or API key. No segment
turns one generation into 40 cloud requests; provider-backed work is
presenter-controlled with the reviewed local result already on screen.

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
flag, not auth; anyone who knows it gets the panel too.

Attendees use the Network URL vite prints on startup (your LAN IP,
port 5173), without the flag. Write it somewhere visible.

Prep checklist, in order, on the actual laptop:

1. Throwaway move on the chess-machine page: backend is live.
2. Open the adaptation panel (left of the workspace grid on the
   chess-machine page). Train the adapter on the reference snapshot,
   then run base and adapted benchmarks (replayed). The Compare step
   must show its table before anyone arrives: the outcome reveal in
   segment 4 depends on it.
3. On each modality page, run "Show adaptation evidence" and "Reveal
   cached artifact" once: the image pair, both audio clips, and both
   video takes must render and play from local files with no network.
4. Deck on 3030, LiveRoom slide shows the room. Open the deck tab with
   presenter mode and speaker notes.
5. If OPPONENT_MODELS/keys are set, start one throwaway game to see the
   model answer; if not, the fallback plan below covers it.
6. `just session-notebook` once, then close it: JupyterLab starts cold
   in seconds when segment 8 arrives.

Presenter controls (top of the board with `?presenter=1`): Lock
editing, Unlock editing, Bring everyone to presenter view, Send users
to their workspace, Prev/Next slide while presenting, Reset page, and
the Games room monitor with the two dataset export buttons (Download
SFT dataset, Download all shapes). Presenter actions reach attendee
browsers within a few seconds.

The week before: run the load test once on the actual laptop
(`just mock-llm`, backend pointed at it, `just load-test 40`), and time
this whole run of show once for real.

## Run of show

Each segment lists: target duration and the hard stop, what the room
predicts before the action, what participants do, the one artifact
everyone inspects, the sentence that closes the loop, the cut when
late, and the fallback when something fails.

### 1. Motivation (deck slides 1, 6) - 4 min, hard stop at 0:05

- Predict: nothing yet; state the board URL twice while people settle.
- Participants: open the Network URL, do not join yet.
- Artifact: the cost-of-training versus cost-of-adapting magic-move.
- Close the loop: adapting is the affordable end of moulding
  intelligence.
- Cut: drop the stages-of-AI beat, keep the URL repetition.
- Fallback: none needed; slides are local.

### 2. Chess grounding (deck slides 2-5) - 7 min, hard stop at 0:12

- Predict: ask who has never played; watch the hands.
- Participants: none; this is the personal hook.
- Artifact: the Duolingo streak and Elo counter.
- Close the loop: chess is checkable, so every claim a model makes here
  can be verified by the environment. That is why the whole workshop
  lives in it.
- Queen's Gambit beat stays. Land it, move on.
- Cut: compress rules to one slide pass (the board pages re-teach by
  doing).
- Fallback: none needed.

### 3. The map and the mantra (deck slides 7-11) - 4 min, hard stop 0:16

- Predict: which of the six outcomes (moves, commentary, instruction,
  style, sound, scenarios) they would build first.
- Participants: join the board with their name now. Budget dead air;
  the LiveRoom slide shows joins landing.
- Artifact: the ModalityGrid mantra slide. Say it out loud: pairs in,
  adapter out, eval always.
- Close the loop: everything after this is that sentence, four times.
- Cut: skip slide 9's how-to-follow detail; joining already happened.
- Fallback: if the venue wi-fi blocks the room, continue presenter-only
  and say so; every later segment has a presenter-led mode.

### 4. Outcome-first reveals (board) - 10 min, hard stop at 0:26

Switch to the board. Bring everyone to presenter view.

- Predict: before each reveal, one guess out loud. Text: how many of
  twelve held-out positions does the base model answer legally?
  Audio/video: which take is the adapted one?
- Participants: watching your screen (their cameras are driven);
  shout predictions.
- Artifacts, in order, one inspection each:
  1. Adaptation panel, step 5: the comparison table. Legality
     7/12 to 12/12 improved, JSON validity up, explanation rate 0.75
     to 0.00 regressed. Open one example: the chatty base reply next
     to the adapted bare JSON.
  2. Image page, Show adaptation evidence: the watercolor pair.
  3. Audio page, Show adaptation evidence: play base then adapted
     motif; the waveforms show the level ramp.
  4. Video page, Show adaptation evidence: play the flickery base
     take, then the steady one; the frame strip is the receipt.
- Close the loop: same recipe, four modalities, and one metric got
  worse every time. Adaptation trades.
- Cut: drop the per-example text inspection; keep all four reveals.
- Fallback: every file is local and committed; if a panel fails to
  load media it says so in words. Worst case, `just reset-db && just
  seed` restores state in seconds (canvas untouched).

### 5. The shared game (board) - 14 min, hard stop at 0:40

Send users to their workspace. Unlock editing.

- Predict: whether the small local model will beat them; whether their
  own moves are all legal.
- Participants: hands-on. Double-click their workspace, Start game
  (five minutes), play the configured model. Open one dataset tab
  before moving and leave it open: the newest row replaces the old one
  in place. That is the aha; do not rush it.
- Artifact: their own dataset rows, plus one illegal-move attempt on
  purpose: board unchanged, reward -1. If the model answers garbage,
  celebrate: the failed attempt lands in model_attempts, the turn
  retries, and after the budget a labelled fallback move plays. Run
  the two text jobs (prompt eval, reward eval) and read the live
  numbers next to the cached ones (the eval rows now open into
  definitions and provenance).
- The two-game beat when OPPONENT_MODELS is set: one game against the
  small model, one against the frontier model. Same recipe, same
  board, different results, felt.
- Scenario beat: Assess position on a mid-game moment; accept or edit
  the mapping. Keep Ramon's aside: rage-quitting against the bot is a
  labeled data point now.
- Close the loop: pairs in. Everything they just made is the left side
  of the mantra.
- Cut: one game instead of two; skip the scenario beat (segment 6's
  freeze still shows raw/approved counts from rehearsal data).
- Fallback: no key or provider down means Start game reports the model
  unavailable with a retry button; play a free-play game against a
  volunteer instead and narrate the same dataset rows. The mock LLM
  (`just mock-llm`) is the rehearsal stand-in, not a live-room tool.

### 6. The adaptation evidence chain (board) - 12 min, hard stop 0:52

Bring everyone to presenter view. Adaptation panel, top to bottom.

- Predict: what a training run needs to be reproducible. Collect three
  answers before opening the panel.
- Participants: watching; two called-out checks (do the hashes match
  between adapter card and snapshot card; which metric regressed).
- Artifacts, one per step:
  1. Freeze room dataset: the new snapshot card with eligible versus
     excluded counts, scenario raw/approved, and its content hash.
  2. Config card: LoRA parameters, seed, output task, config hash, and
     the three Gemma roles behind the disclosure.
  3. Train adapter on the reference snapshot: adapter card, result
     source cached, runner replay. Then select the just-frozen room
     snapshot and train again: read the 409 out loud. The cached
     result is bound to the reference hash and will not pose as
     training on the room's data. That refusal is the honesty model.
  4. Run base and adapted benchmarks (replayed). Optionally, with a
     key configured, Run base live: watch the run list show live
     provenance, and if a call fails, the run's position set differs
     and Compare says Not comparable per metric. Do not fish for this;
     mention it when it happens.
  5. Compare: deltas with verdict words, the regression on screen, and
     one example opened.
- Close the loop: adapter out, eval always. An adapter without a
  dataset hash is a rumor; a delta without a matching frozen set is
  decoration.
- Cut: skip the live base run and the refusal beat; keep freeze,
  train, compare.
- Fallback: everything here is fixture-backed and keyless by design;
  the live button only exists when credentials do.

### 7. Decomposition (deck slides 12-17, 19-24) - 6 min, hard stop 0:58

Back to the deck, fast pass.

- Predict: which stage of the chain costs the most in each modality.
- Participants: none; this is naming what they saw.
- Artifact: DatasetShapes cycling one move through six encodings; the
  training ladder magic-move; the per-modality what-changes slides;
  merging's slerp YAML.
- Close the loop: the recipe never changed; the failure modes did.
- Cut: drop merging (slide 24) first, then the ladder animation.
- Fallback: none needed; slides are local.

### 8. Notebook practice (standalone Jupyter) - 12 min, hard stop 1:10

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

### 9. Close (notebook, then the room) - 3 min, hard stop 1:13

- Restate the four outcomes as questions; let the room answer.
- Repo link and resources from the notebook's final section (the deck
  is not reopened for this).
- The economics point, briefly: open models, falling barriers,
  intelligence choice.

Core total: 72 minutes at the hard stops. The remaining 18 absorb
joins, questions, and failures; if nothing goes wrong, segments 5 and
8 stretch to fill.

## If something goes wrong mid-session

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
  segment 6. Nothing else in the core touches a provider.
- App unusable entirely: `just session-notebook` opens the standalone
  notebook and the session continues from segment 8's material; the
  committed media under `artifacts/cached/media/` can be opened
  directly from the filesystem if a reveal is needed.

## Timing evidence

Rule: time the walkthrough on the real laptop, do not estimate it from
headings. Record the measured core duration, what was skipped, and
every wait on the system. The phase-34 rehearsal measurements and the
current cut list live in
[notes/ai/phase-34-learning-experience.md](../notes/ai/phase-34-learning-experience.md);
re-measure after any structural change to this file.
