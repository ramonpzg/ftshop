# Deck plan, v2

Here is how I am thinking about the deck and the flow.

My style is many slides, plenty of movement, and very few words. Russell
Davies is a useful reference. The deck should feel black and white, composed,
and quick. The whiteboard remains hand-drawn. The notebook remains pragmatic.

This version keeps the personal beats from v1. Some may come out after a full
rehearsal, but they are cheap for me to add and useful when I need a controlled
narrative in front of a room. Do not remove the dog-thinking meme, "what could
possibly go wrong", "Cool bruh", the cookie GIF, the goth Minions, or the
corporate-lamp paragraph while implementing this plan.

The non-linear order is intentional. The TUI appears before the chess recap.
People may not play chess, but they understand a terminal game when they see
one. The recap later explains the objects they have already seen.

Split the implementation by narrative section so each part can be revised
without loading one enormous file:

```text
slides.md
slides/01-origin.md
slides/02-outcomes.md
slides/03-why-adapt.md
slides/04-chess-primer.md
slides/05-technical-reference.md
```

Use Slidev imports from the root file. These are section boundaries, not
independent mini-decks. Shared components, styles, slide numbers, and speaker
notes still belong to one presentation.

## Delivery guardrails

- The opening deck should take 20 to 25 minutes, including the TUI recording
  and audience responses. It may contain many slides because most are one
  visual beat, not one minute of speaking.
- Prefer another slide with object continuity over seven unrelated click
  layers on one slide. Use clicks when the audience must compare the previous
  state with the next one in the same frame.
- Every educational transition is presenter-controlled. Nothing advances on a
  timer.
- Visible text is terse. The personal detail lives in my delivery and speaker
  notes.
- Every model example has a source, exact input, model or adapter identity, and
  cached/live label. A prompted pipeline is not presented as fine-tuning.
- Cost comparisons state the task and target quality. A small adapted local
  model is not described as generally equivalent to a frontier API model.
- Prices are placeholders until checked close to the session. Every final
  number gets a source and access date.
- The outcome slides work from local files. A provider request is an optional
  live replacement, never the only thing the room can see.

## Default and fallback routes

Default route:

1. Deck: personal origin, TUI outcome, modality outcomes, why adapt, minimum
   chess representation.
2. Whiteboard: the room plays, produces data, and inspects the adaptation
   evidence.
3. Notebook: the practical code walkthrough and participant work.
4. Optional two-minute whiteboard coda: show what the room produced. This is a
   result, not another explanation.

If the whiteboard fails, stay in the deck long enough to show the pinned model
outputs through its components, then jump directly to the notebook. Do not
spend ten minutes repairing collaboration in front of the room.

If time runs short, skip the technical-reference section in the deck. The
notebook contains the details and remains useful on its own.

## Part 1: where this came from

### Slide 1: title

**Visible:** session title and the four modalities.

**Visual:** one strong chess image or the actual TUI board, not a generic AI
illustration.

**Say:** one sentence on the workshop: we will use chess to inspect the same
adaptation recipe across text, image, audio, and video.

**Hard stop:** 30 seconds.

### Slide 2: this is what I looked like when I discovered chess

**Visual:** old picture of me, full enough to read from the back.

**Click:** the book appears as a second physical object, not in a card.

**Say:** I bought a book and everything to get better at it, opened it five
times, never saw it again, was not any good, and stopped playing.

**Guardrail:** do not explain chess yet. This is origin, not instruction.

### Slide 3: fast forward to April 2026

**Visual:** the Duolingo chess launch post.

**Say:** chess mode launched earlier. I only noticed it in Japan when I opened
the app to practise Japanese.

**Click:** the app image takes over the launch post.

### Slide 4: Oscar and I became best friends

**Visual:** one game, then Oscar.

**Motion:** the same phone frame remains in place while its contents change.

**Say:** the main player and I became best friends. This is allowed to sound
slightly ridiculous because it happened.

### Slide 5: 5, 20, 500

**Visual:** one counter or stack of game records.

**Clicks:** 5 games a day, 20 games a day, then 500 games in the first month.

**Final click:** Queen's Gambit image.

**Say:** I got hooked and watched it for the first time.

**Guardrail:** numbers must match the record I want to tell on stage. Do not
invent an Elo or total-game number around them.

### Slide 6: no Internet

**Visual:** the Duolingo chess screen rendered useless on the Sydney flight.

**Say:** on the way back from Japan I could not play. That is the constraint
that matters: the opponent I wanted disappeared with the connection.

### Slide 7: a reasonable response to that problem

**Click 1:** dog-thinking meme.

**Say:** surely people have fine-tuned models on chess moves. Has anyone
explained the complete process, released the evidence, and then done something
personal with it?

**Click 2:** "what if I completely change what I had planned for my talk with
less than a month to go"

**Click 3:** "what could possibly go wrong"

**Guardrail:** these stay because they help me command the room. Keep the
visible words short and let me do the setup.

### Slide 8: TUI recording

**Visual:** phone-shaped recording of the actual Termux TUI, large and
uncropped. The chess board must be readable from the back of the room.

**Show in the recording:** start the local llama.cpp server, open the TUI,
play at least one participant move and one Gemma move, show the dry commentary,
open the game record, and step through a short replay.

**Say:** this is the end goal in one object. It runs on my phone, records wins,
losses and draws, keeps the moves, and lets me replay the game. Its commentary
is sassy as fuck. The model commentary is not Stockfish analysis and should not
be sold as one.

**Click:** the Art of War quote or the concrete objective appears: win while
taking as few opposing pieces as possible.

**Guardrail:** phrase the objective without the double negative. Prefer an
actual recorded result such as `win, 2 captures` when one exists.

**Fallback:** the video is local and has a poster frame. Do not demo the phone
live unless I choose to.

## Part 2: four adaptation problems

### Slide 9: four adaptation problems, one domain

**Visible:** Text, Image, Audio, Video.

**Say:** these are four adaptation problems, not necessarily four model
processes. The text path alone may use a player model and a scenario writer.

**Motion:** one chess game remains fixed while the output around it changes.

### Slide 10: text can do more than choose a move

**Visual:** a completed board, game log, and one detailed real-world mapping.

**Say:** the game model chooses moves. A separate text workflow can map the
same sequence to a situation at work, at home, or in sport. Those mappings can
become their own reviewed dataset.

**Guardrail:** label Luna as the scenario writer when Luna produced it. Do not
call that output a fine-tuned chess model result.

### Slides 11 to 13: three real-world mappings

Use one example per slide. Keep the board and log in the same location so the
description change is the event.

Each example carries:

- the exact game or final FEN;
- the raw model mapping and approved edit when they differ;
- model and prompt version in a small disclosure;
- no chess pieces in the later video prompt.

Three examples are allowed in the build. One or two can be skipped during the
session without breaking the argument.

### Slide 14: image adaptation

**Visual:** an actual board and pieces in one specific theme.

**Clicks:** base output, adapted output, then a second style if it earns the
time.

**Say:** the useful question is not whether it looks cool. The pieces still
need to be identifiable and the style needs to hold across the full set.

**Evidence:** same prompt where possible, adapter/model identity, seed,
dimensions, piece-identity check, and style-adherence check.

### Slide 15: audio adaptation

**Visual:** board plus native audio control and one compact waveform or
spectrogram.

**Clicks:** capture sound, background or genre example, optional spoken move.

**Say:** audio can cover captures, music, room tone, or speech. These are
different tasks and should not be presented as one adapter doing everything.

**Guardrail:** no autoplay. MusicGen is enough for the local path. Stable Audio
is optional.

### Slide 16: video from the real-world case

**Visual:** the detailed Luna scene description first, then the video it
produced.

**Clicks:** scene prompt, poster, playback.

**Say:** LTX, Gemini, or another video model stages the real-world situation.
It is not trying to animate a chess move. That looked bad and was not the
interesting part anyway.

**Guardrail:** the generated scene contains no board, pieces, move notation,
or giant chess metaphor unless the source mapping explicitly requires one.

### Slides 17 to 20: which one was adapted?

Give each modality one uncluttered A/B slide rather than asking the audience to
remember eight outputs on one screen:

1. text;
2. image;
3. audio;
4. video.

Ask which is base and which is adapted. Do not reveal yet if the room is
engaged. If it is quiet, reveal each answer immediately and keep moving.

Only use actual adapted/reference pairs from Hugging Face, fal, or our own
training. Record the model card, adapter, license, input, and parameters. If
the pair does not share a controlled input, call it an adapted/reference pair,
not a controlled before/after experiment.

### Slide 21: reveal

**Visual:** one restrained table, one row per modality.

**Clicks:** reveal each row.

Each row shows:

- answer;
- exact target behavior;
- one relevant metric with sample size;
- cached or live provenance;
- one limitation or regression.

At least one adapted result must improve the target and get worse somewhere
else. Fine-tuning is a trade, not a ceremony where every score rises.

## Part 3: why adapt anything?

Keep these slides in the build. Rehearsal decides whether some are skipped.

### Slide 22: why fine-tune, economics at a target quality

Keep the four rows, but do not frame them as general head-to-head model
equivalence.

Reveal one row at a time:

1. **Text:** Gemma base/adapted on the exact legal-move JSON task versus the
   configured API model on that task. Show legal rate, JSON rate, latency,
   device, and marginal request cost.
2. **Image:** base/style-adapted FLUX on local or rented hardware versus an API
   reference using the same prompt. Show identity/style result, seconds, and
   cost.
3. **Audio:** MusicGen base/adapted locally versus an API reference for the
   same prompt and duration. Show adherence, clipping, latency, and cost.
4. **Video:** LTX on rented hardware versus the configured API video path for
   the same saved scene prompt. Show case adherence, continuity, duration,
   generation time, and cost.

The comparison includes training or rental cost, hardware amortisation,
request volume, and the quality threshold being met. Use `[SOURCE, DATE]`
placeholders until checked. Never imply that fine-tuning alone caused a lower
serving bill.

### Slide 23: providers do not have your data

**Visible:** public corpus on one side, the examples needed for this exact
behavior on the other.

**Say:** the general model has not seen the private, licensed, reviewed, or
newly-created examples that define the task. Hosted fine-tuning still sends
data to a provider; local ownership and fine-tuning are related decisions, not
the same decision.

### Slide 24: providers do not know your style

Keep these click beats:

1. goth Minions;
2. the super jargon-heavy paragraph about the new lamps on employees' desks;
3. bachata background music or the Thinking Machines slang-to-corporate
   translation clip;
4. the real Canva video-template example.

**Guardrail:** end on Canva because it is the concrete case. The earlier beats
set up personality; the real example carries the claim.

### Slide 25: the data we can actually use

Keep the expanding and overlapping circles, but make each boundary precise:

1. data we think exists;
2. data we can access;
3. data we can legally use;
4. data relevant to the task;
5. private or newly-created data outside the public circles.

**Final click:** split the useful set into training and held-out evaluation.
The same examples do not get to prove both that we learned and that we
generalised.

### Slide 26: Cool bruh, what now?

**Visual:** chunky boy deciding which cookie to eat.

Keep this beat. It releases pressure before the decision slide. Do not add
more copy around it.

### Slide 27: choose the intervention, not a tribe

**Visual:** four direct options.

- Prompt for instructions that change per request.
- Retrieve facts that change or need citations.
- Use tools for rules and exact calculations.
- Fine-tune repeated behavior that examples define better than prose.

**Say:** we can combine these. The chess app already does: python-chess owns
legality, the prompt supplies the position, and an adapted model can learn how
to choose and explain.

### Slide 28: keep the options

**Visible:** use the hosted model when it is the better tool; own an adapted
model when the repeated task, data, latency, or offline requirement justifies
it.

This replaces the broad claim that we can mould all intelligence to our will
with something I can defend using the examples already shown.

### Slide 29: what the model tree may become

**Visual:** the future tree diagram from v1.

**Say:** one general model, several adapters, merged variants, local aliases,
and provider models can coexist. We are not at the effortless version of that
yet.

**Cut:** optional. Remove during delivery if it does not lead directly into
the technical section.

### Slide 30: enough preamble, let's get started

Keep the line. It acknowledges the transition and gives me a clean reset.

## Part 4: the chess objects, after we have seen them

### Slide 31: chess rules recap

**Visual:** one board, not a wall of piece rules.

Cover only what the rest of the workshop needs: turns, legal moves, check,
checkmate, captures, promotion, and castling. En passant can remain in the
notebook or appear only if someone asks.

The delayed recap is deliberate. The audience has already seen the game and
now gets names for what happened.

### Slide 32: one position, four representations

Keep the board fixed and morph the labels around it:

1. FEN stores the position;
2. UCI names a move for machines;
3. SAN names a move for people reading a game;
4. PGN stores the game history.

Use the same actual move in every representation. Do not list notation that
the workshop never consumes.

### Slide 33: Stockfish has one job here

**Visible:** Model proposes. Rules engine validates. Stockfish evaluates.

**Say:** Stockfish is not the fine-tuned model and it is not the dataset. It is
an optional oracle for move quality, centipawn loss, and tactical checks.
python-chess handles legal state transitions without pretending to evaluate
strategy.

## Part 5: technical reference and interactive components

This section redesigns the existing "Building a Chess Machine" and modality
slides. It exists in the deck, but it is modular. The default workshop path
may cover some of it on the whiteboard or in the notebook instead.

Required beats:

1. the recipe: pairs in, adapter out, eval always;
2. one move becoming six honest dataset rows;
3. prompt, chat template, and constrained move reply;
4. base and adapted checkpoints on one frozen evaluation suite;
5. the training ladder: UI, API, Axolotl, Unsloth, raw JAX;
6. image, audio, and video differences in data and evaluation;
7. merging and what it can damage.

Required components or component families:

- `PhoneTuiReplay`: local video with poster and explicit play control;
- `OutcomeCompare`: matched input, base/adapted outputs, metrics, regression;
- `DatasetShapes`: same move changing representation;
- `RewardMeter`: environment feedback separated from model output;
- `CostAtTarget`: one task, target quality, measured deployment facts;
- `DataUniverse`: the circle sequence and train/eval split;
- `NotationMorph`: board, FEN, UCI/SAN, PGN with object continuity;
- `LiveRoom`: real room state with a useful offline state;
- modality-native image, audio, and video renderers with pinned results.

The later deck-fallback phase adds the Local/API profile dropdown and live
backend routing. This plan should leave stable space for it but should not
invent provider selectors inside each slide.

## Speaker-note contract

Every slide gets:

- `TIMING`: target and hard stop;
- `SAY`: the argument, not a paragraph to read;
- `CLICK`: what changes and why;
- `SOURCE`: image, quote, model, cost, or dataset provenance;
- `CUT`: what happens if skipped;
- `FALLBACK`: what remains when the backend, phone, or provider is unavailable.

The notes are the guardrails. They should be explicit enough that I can trust
the narrative without auditing every implementation detail during delivery.

## Assets and provenance

- Use the actual childhood photo, book image, Duolingo screenshots, TUI
  recording, model outputs, and generated media wherever possible.
- Keep local copies of every workshop-critical image, audio file, video,
  poster, and fixture. Temporary provider URLs do not count.
- Record source and license for the Duolingo launch post, Queen's Gambit image,
  memes, Minions image, quote, Thinking Machines clip, and every model output.
- The deck can contain placeholders I will fill. Make the placeholder's final
  geometry explicit rather than inventing replacement content.
- The black-and-white editorial treatment belongs to the deck. Do not import
  the whiteboard's hand-drawn visual system into it.

## Rehearsal decisions

After the complete build exists, time it before cutting. Decide from evidence:

- whether all three real-world mappings stay;
- whether every A/B question waits until the combined reveal;
- whether slides 22 to 29 all fit;
- whether the future model tree earns its transition;
- whether the Art of War quote helps the TUI objective;
- whether the session finishes in the notebook or uses the two-minute
  whiteboard coda.

Do not remove the named personality beats during implementation. Mark them as
cuts in speaker notes so I can make those decisions during rehearsal.
