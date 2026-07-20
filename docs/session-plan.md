# Session plan

Same Recipe, Different Results: Fine-Tuning Models Across Modalities.
EuroSciPy 2026, advertised at 90 minutes. One shared domain: chess.
Four modalities: text, image, audio, video.

This is the narrative plan: what the session teaches, in what order,
and why. The deck's slide-by-slide build lives in `deck/PLAN_V2.md`,
which is the authoritative narrative decision; this file follows it.
The minute-by-minute run of show with every app and deck transition is
[demo-plan.md](demo-plan.md). How the app is put together is
[architecture.md](architecture.md).

The order is outcome-first and deliberately non-linear: the TUI and
the modality outcomes appear before the chess recap. People may not
play chess, but they understand a terminal game when they see one; the
recap later names the objects they have already watched. Sections stay
modular so Ramon can reorder after rehearsal without rebuilding slides
or panels.

## Outcomes

By the end, a participant can demonstrate four things:

1. **Turn play into training pairs.** Play moves on their own board,
   point at the dataset rows those moves generated, and say why a
   fallback move stays in the audit archive but never enters the SFT
   snapshot.
2. **Trace an adapter to its evidence.** Read the adapter card and name
   what makes it reproducible: base checkpoint, dataset content hash,
   config hash, runner, and whether the result was scripted, cached,
   or live.
3. **Judge an adaptation honestly.** Read the base-versus-adapted
   benchmark over one frozen suite, quote the metric that improved and
   the one that regressed, and say why the delta is valid at all:
   matching position sets and one prompt contract.
4. **Carry the recipe across modalities.** For image, audio, and video,
   name the pairs, the adapter, and the evaluation evidence in each
   chain, and one thing that changes per modality.

Everything else in the session serves those four.

## Why this session

Not a claim that we can mould all intelligence to our will; a claim
Ramon can defend with the examples on screen. There are four honest
interventions for shaping model behavior: prompt for instructions that
change per request, retrieve facts that change or need citations, use
tools for rules and exact calculations, and fine-tune repeated
behavior that examples define better than prose. The chess app
combines them on purpose: python-chess owns legality, the prompt
supplies the position, and an adapted model can learn how to choose
and explain. Use the hosted model when it is the better tool; own an
adapted model when the repeated task, the data, latency, or an offline
requirement justifies it. The session exists to make that decision
concrete four times over.

## Timing budget

Core teaching: 70 minutes. Controlled flex: 20 (join dead air,
questions, recovery, the optional coda, and rehearsal-decided cuts).
The advertised length stays 90. Segment-level hard stops and cut lists
are in the run of show.

| # | Segment | Asset | Core minutes |
| --- | --- | --- | --- |
| 1 | Where this came from, ending in the TUI | deck part 1 | 9 |
| 2 | Four adaptation problems, which one was adapted | deck part 2 | 8 |
| 3 | Why adapt anything | deck part 3 | 5 |
| 4 | The chess objects, after we have seen them | deck part 4 | 3 |
| 5 | The shared game | board | 15 |
| 6 | The adaptation evidence chain | board | 13 |
| 7 | Notebook practice | notebook | 14 |
| 8 | Close | notebook | 3 |
| - | Optional coda: what the room produced | board | (2, flex) |

The deck opening (segments 1-4) targets 20 to 25 minutes including the
TUI recording and audience responses, per PLAN_V2: many slides, one
visual beat each. The deck's part 5 (technical reference) is modular
and is not a scheduled segment; the default path covers that material
on the whiteboard and in the notebook, and the deck section exists for
questions and time to spare. If time runs short it is the first thing
that never happens.

Asset order: deck first, collaborative whiteboard second, standalone
Jupyter notebook as the closer, with an optional two-minute whiteboard
coda showing what the room produced -- a result, not another
explanation. The session does not return to the deck to restate the
close.

## 1. Where this came from (deck part 1)

The personal origin, told with Ramon's own artifacts: the childhood
chess encounter and the book that got opened five times; the Duolingo
chess launch discovered in Japan; Oscar; 5 games a day, then 20, then
500 in the first month (the numbers match the record, and no Elo or
total-game figure is invented around them); the Queen's Gambit watched
for the first time after getting hooked; the Sydney flight with no
Internet, where the opponent disappeared with the connection. That
constraint is the motivation. Then the reasonable response: surely
people have fine-tuned models on chess moves; has anyone shown the
complete process with evidence and made it personal? The personality
beats (the dog-thinking meme, "what could possibly go wrong") stay,
per PLAN_V2.

The payoff is the TUI recording: the actual Termux app on a phone,
playing local Gemma through llama.cpp, with the game record, the
replay, and commentary that is sassy as fuck (labelled as flavor, not
Stockfish analysis). One object that already contains the whole
workshop: local model, real rules, recorded evidence, personal
objective -- win while taking as few opposing pieces as possible.

No chess instruction happens here. This is origin, not a rules class.

## 2. Four adaptation problems (deck part 2)

Text, image, audio, video as four adaptation problems, not four
interchangeable model processes. The text path alone may use a player
model and a scenario writer, and Luna is always labelled as the
scenario writer, never as a fine-tuned chess model. Three real-world
mappings from games, with raw versus approved text and provenance in
small disclosures.

Then the A/B beat, one uncluttered slide per modality: which output
came from the adapted model? Predictions from the room, then the
reveal table: answer, exact target behavior, one metric with sample
size, cached or live provenance, and one limitation or regression per
row. At least one adapted result improves its target and gets worse
somewhere else; fine-tuning is a trade, not a ceremony where every
score rises. Every pinned output works from local files; a provider
request is an optional live replacement, never the only thing the
room can see.

## 3. Why adapt anything (deck part 3)

Economics at a target quality (per task, with sources, never a general
head-to-head equivalence claim). Providers do not have your data: the
private, licensed, reviewed, or newly-created examples that define a
task, and the split between what trains and what proves
generalisation. Providers do not know your style, carried by the named
personality beats and landed on the concrete Canva case. Then the
decision slide: prompt, retrieve, tools, or fine-tune -- choose the
intervention, not a tribe -- and keep the options.

## 4. The chess objects, after we have seen them (deck part 4)

The delayed recap, deliberate: the audience has watched games happen
and now gets names for what they saw. One board; turns, legal moves,
check, checkmate, captures, promotion, castling. One position in four
representations: FEN stores the position, UCI names a move for
machines, SAN for people, PGN stores the history, all with the same
actual move. Stockfish has one job: an optional oracle for move
quality; python-chess owns legal state transitions; the model
proposes. En passant lives in the notebook unless someone asks.

## 5. The shared game (board)

The main participation block. Attendees play a timed match against the
configured model on their own board and watch the dataset panel build
rows from their moves: PGN prefix, FEN to move, FEN plus legal moves,
board tensor, policy and reward, RL trajectory. An illegal attempt
scores reward -1 and moves nothing, which is the RL environment lesson
happening live. A model reply that fails legality lands in
model_attempts, retries, and falls back with a label after the budget;
garbage never poses as skill. The per-exchange scenario mapping turns
the game into real-world cases with participant review. The two-model
beat (small local Gemma, then a frontier model) makes "same recipe,
different results" physical before any training talk.

## 6. The adaptation evidence chain (board)

The presenter runs the whole loop from the adaptation panel, no shell.
The panel says up front what the room must know: this chain is a
scripted illustration, no model was trained, and only a live base run
calls a real model.

1. Freeze the room's dataset. Row counts, excluded fallback rows,
   source games and workspaces, raw versus approved scenario counts,
   schema version, content hash.
2. Show the training config: base checkpoint, LoRA parameters, seed,
   output task, config hash, and the three Gemma roles kept distinct
   (unquantized training start, GGUF inference repo, serving alias).
3. Train. The result is a scripted replay and the panel says so. Then
   try to train on the just-frozen room snapshot: the backend refuses,
   because the scripted result is bound to the reference snapshot by
   content hash and will not pose as training on anything else. The
   refusal is the lesson.
4. Benchmark base and adapted on the frozen held-out suite. Twelve
   examples with durable ids, one deliberately duplicated position,
   every attempt tagged with checkpoint and replayed/live provenance.
5. Read the comparison: legality up, JSON validity up, and the
   explanation rate collapsed -- the contract invites an optional
   in-JSON reason, the base model often fills it, and the adapter
   trained on bare completions never does. Adaptation trades. A
   mismatched position set renders as "Not comparable" with the
   reason, never as a number.

## 7. Notebook practice (standalone Jupyter)

A deliberate switch: open `notebooks/full-session.ipynb` in its own
JupyterLab via `just session-notebook`. This is the pragmatic
take-home. Participants follow the end-to-end material and can load
the exact `chess_sft.jsonl` the room exported. Provider and
local-model cells are optional and presenter-rehearsed; no attendee
needs a key. The notebook refers back to the whiteboard's frozen-hash
story instead of repeating it.

## 8. Close, and the optional coda

Restate the four outcomes as questions the room can now answer; point
at the repo and resources from the notebook's final section. When time
allows, the two-minute whiteboard coda: the room's own games, rows,
and frozen snapshot on screen -- a result, not another explanation.
Open models keep matching what closed models did months ago, the
barrier keeps falling, and owning an adapted model is now a real
option among the four interventions.

## Participation honesty

Assume up to 40 attendees and venue Internet that drops after idle
minutes and demands a captive portal. The core path therefore runs on
the presenter's machine and reviewed local fixtures: no attendee needs
a provider account or API key, and no core segment multiplies one
generation into 40 cloud requests. The backend enforces this: paid or
live generation only runs from the presenter's own machine, whatever a
browser asks for. Text is fully hands-on (own board, own game, own
rows). Image drawing is hands-on when drawings are persisted and
inspected; provider-backed generation is presenter-led with the pinned
local pair already visible. Audio and video are presenter-led by
default; attendees get prediction and comparison tasks (which take is
adapted, which metric regressed) instead of a pretend hands-on. The
run of show marks each segment's mode.

## Delivery setup

The app is a local-first tldraw whiteboard with a shared sync room.
Options for the room, in order of preference:

1. Presenter hosts one copy, binds it to the local network, and shares
   the URL over the venue wi-fi. This is what `just start` supports
   today.
2. A hosted copy on Fly.io or similar as a fallback, so a copy is
   always reachable and the presenter's laptop is just another client.
3. Everyone runs the app on their own device and follows along locally.
   Slowest to set up, but immune to bad wi-fi.

As someone joins they enter their name, get an ID, and the app creates
a workspace for them: a chess board, a dataset panel, a mini IDE, a
config panel, an artifact panel, and an eval panel. As they play, the
dataset builds on screen as JSON. Presenter controls pull everyone to a
section and send them back to their workspaces.

If the whiteboard fails, stay in the deck long enough to show the
pinned outputs through its components, then jump to the notebook. Do
not spend ten minutes repairing collaboration in front of the room.

## Topic reference per modality

Material available when questions go deep, largely covered by the
deck's modular part 5. None of it is a scheduled lecture.

**Text.** Data formats (the six shapes in docs/datasets.md). SFT
teaches what good answers look like; RL teaches what good actions do;
chess validates every action. Illegal-move handling at app and model
level. Stockfish and where it fits. Prompt and chat templates, Jinja.
Model choice: base or RL'd checkpoint, one player model or player plus
analyst. The training ladder from Unsloth Studio to raw JAX. LoRA
versus QLoRA versus full fine-tuning. Hardware.

**Image.** Everyone draws their favourite piece; persisted drawings
become (image, caption) pairs with a trigger word. Diffusion versus
transformers. What providers quietly do to prompts. Captions, aspect
ratios, output dimensions; dataset size sensitivity. The approach
taxonomy from text-to-image through image editing. Candidate model:
Flux 2 Klein 4B. Why models struggle to write text on images.

**Audio.** What audio covers, from music to real-time voice. Chess
ideas: intensity music, capture sounds, an illegal-move buzz, a
narrator. Sound is vibration, audio is its representation, a
spectrogram makes it an image. MusicGen locally; Stable Audio as the
gated, optional alternative. The click synth: you can also just make
the sound yourself.

**Video.** Luna writes a real-world case and a filmable scene prompt
per game; the generated video stages that case and never shows a
chessboard. Frame sampling, temporal consistency, compute that
escalates faster than expected. LoRA on a recent LTX model; costs are
cents per second, said out loud.

## Session description (as submitted)

Fine-tuning has become the default way to adapt foundation models to
specific tasks, but most of the conversation focuses on text. If you
have fine-tuned an LLM with LoRA or QLoRA, you might assume the jump to
other modalities is straightforward as the core idea is the same. In
practice, each modality comes with its own assumptions, failure modes,
and hard-won lessons that only become obvious once you start training.

This talk walks through fine-tuning across four modalities side by side,
highlighting the patterns that hold and the ones that break.

For text (LLMs), we start with the standard recipe as a baseline (LoRA,
dataset formatting, evaluation), and focus on identifying the implicit
assumptions in the text workflow that do not carry over to other
modalities.

For images (diffusion models), we walk through fine-tuning for specific
visual styles that look similar on the surface, but for which the data
preparation is fundamentally different. We cover why image adaptation is
far more sensitive to dataset size and composition than text, and the
tradeoffs between techniques.

For audio, we look at fine-tuning a model to generate music in a
specific genre using publicly available data, and how audio tagging
models can be paired with embeddings to build applications that connect
generation with semantic understanding of music.

Video, as the least documented modality, has frame sampling strategies,
temporal consistency, and compute requirements that escalate faster than
you would expect. We cover the current state of video model adaptation
and where the tooling still has rough edges.

Once you have multiple fine-tuned models, merging offers a way to
combine their capabilities without retraining. We cover the main
strategies and when merging is a shortcut worth taking versus when it
will produce sub-optimal outputs.

Across all modalities, we compare data preparation, training
configuration, evaluation, and the current state of open-source tooling.
All code examples use Python with Hugging Face Transformers, Diffusers,
and related libraries, and every example uses publicly available models
and datasets.

The goal is to give you the comparative mental model that makes moving
between modalities far less intimidating, and to show that with the
right tools and a bit of curiosity, the same recipe can produce very
different and very satisfying results.
