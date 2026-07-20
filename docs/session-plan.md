# Session plan

Same Recipe, Different Results: Fine-Tuning Models Across Modalities.
EuroSciPy 2026, advertised at 90 minutes. One shared domain: chess.
Four modalities: text, image, audio, video.

This is the narrative plan: what the session teaches, in what order,
and why. The minute-by-minute run of show with every app and deck
transition is [demo-plan.md](demo-plan.md). How the app is put together
is [architecture.md](architecture.md).

The structure is outcome-first: participants see finished results
before any mechanism is explained, then the session decomposes what
they saw. Sections are modular on purpose; Ramon can reorder them after
rehearsal without rebuilding slides or panels.

## Outcomes

By the end, a participant can demonstrate four things:

1. **Turn play into training pairs.** Play moves on their own board,
   point at the dataset rows those moves generated, and say why a
   fallback move stays in the audit archive but never enters the SFT
   snapshot.
2. **Trace an adapter to its evidence.** Read the adapter card and name
   what makes it reproducible: base checkpoint, dataset content hash,
   config hash, runner, and whether the result was cached or live.
3. **Judge an adaptation honestly.** Read the base-versus-adapted
   benchmark over one frozen suite, quote the metric that improved and
   the one that regressed, and say why the delta is valid at all:
   matching position sets and one prompt contract.
4. **Carry the recipe across modalities.** For image, audio, and video,
   name the pairs, the adapter, and the evaluation evidence in each
   cached chain, and one thing that changes per modality.

Everything else in the session serves those four.

## Why this session

Fine-tuning is moulding intelligence. It gives shape to a future where
we interact with AIs of all sorts of personalities, skills, and
aptitudes, all while keeping a general level of intelligence far above
the average human and fitting in the devices we already own.

For that to happen we need mediums that expose the flexibility of a
model's internals while giving its complexity more layers than a
croissant. Depending on what someone needs, they chew as much of the
mechanics of fine-tuning as they want. To be fair, the $20 a month we
pay today is not bad at all. The point is not to drop those services.
The point is that we can also have our own AI.

## Timing budget

Core teaching: 72 minutes. Controlled flex: 18 minutes (join dead air,
questions, recovery, optional stretches). The core is what survives a
bad room; the flex is what absorbs one. Segment-level hard stops and
cut lists are in the run of show.

| # | Segment | Asset | Core minutes |
| --- | --- | --- | --- |
| 1 | Motivation | deck | 4 |
| 2 | Chess grounding | deck | 7 |
| 3 | The map and the mantra | deck | 4 |
| 4 | Outcome-first reveals | board | 10 |
| 5 | The shared game | board | 14 |
| 6 | The adaptation evidence chain | board | 12 |
| 7 | Decomposition | deck | 6 |
| 8 | Notebook practice | notebook | 12 |
| 9 | Close | notebook | 3 |

Asset order: deck first, collaborative whiteboard second, standalone
Jupyter notebook as the closer. The notebook may point back at a deck
slide or a whiteboard frame when it saves repetition; the session does
not return to the deck just to restate the close.

## 1. Motivation (deck)

Why adapt a model instead of only prompting or renting a larger hosted
one: control over behavior, cost at volume, privacy, and models that
fit the devices we own. The stages that got us here, compressed to one
slide: rules, statistics, gradients, transformers, diffusion. No
transformer history lecture, no framework survey, no LoRA math yet;
nothing mechanical before the room has seen a result.

## 2. Chess grounding (deck)

- Why chess is a useful shared domain: legal moves are checkable, every
  game generates data, and the environment can validate every action.
- Ramon's route back in: Duolingo's chess pathway in April, two matches
  a day, then thirty, fifty on the hardcore days, over a thousand
  matches, Elo past 1000. What Elo is.
- The minimum rules and notation a non-player needs: the board, the
  pieces, the goal, what a move looks like in UCI and SAN. Nothing
  more.
- The Queen's Gambit check. Anyone who has not watched it should leave
  and come back when they finish it. Land the joke, move on.
- AI beat grandmasters years ago; chess is more popular than ever.
  Automation changed who plays and why. Sets up intelligence you own.

## 3. The map and the mantra (deck)

A quick map of what fine-tuning can do in this one domain: move
prediction, commentary, personalized instruction, playing style, board
sounds, and the real-world scenario dataset Luna builds from games.
Then the recipe, once, out loud: pairs in, adapter out, eval always.
The whole session is that sentence three times per modality.

Attendees open the board and join with their name during this segment,
so workspace creation never blocks the room later.

## 4. Outcome-first reveals (board)

Results before mechanisms, all four modalities inside ten minutes:

- Text: the base-versus-adapted comparison on the adaptation panel,
  pre-run from reviewed fixtures. The adapted checkpoint answers every
  held-out position with a legal JSON move; the base checkpoint
  rambles, mixes SAN into JSON, and picks two illegal moves. One metric
  improved, one regressed. That regression stays on screen.
- Image: the watercolor style pair, before and after, at inspection
  size.
- Audio: the capture click, then the same motif calm versus sharpened,
  with waveforms.
- Video: the rushed-release scene, flickering base take versus steady
  adapted take, with the frame strip.

Every artifact opens from a panel and is a real local file. The labels
say what is illustrative and what is computed. No mechanism talk yet
beyond the mantra.

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
different results" physical before any training happens.

## 6. The adaptation evidence chain (board)

The presenter runs the whole loop from the adaptation panel, no shell:

1. Freeze the room's dataset. Row counts, excluded fallback rows,
   source games and workspaces, raw versus approved scenario counts,
   schema version, content hash.
2. Show the training config: base checkpoint, LoRA parameters, seed,
   output task, config hash, and the three Gemma roles kept distinct
   (unquantized training start, GGUF inference repo, serving alias).
3. Train. The result is a cached replay and the panel says so. Then try
   to train on the just-frozen room snapshot: the backend refuses,
   because the cached result is bound to the reference snapshot by
   content hash and will not pose as training on anything else. The
   refusal is the lesson.
4. Benchmark base and adapted on the frozen held-out suite. Twelve
   examples with durable ids, one deliberately duplicated position,
   every attempt tagged with checkpoint and replayed/live provenance.
5. Read the comparison: legality up, JSON validity up, explanation rate
   collapsed. The adapter got precise and went mute, because nothing in
   the training pairs asked it to keep explaining. Adaptation trades;
   it does not just win. A mismatched position set renders as "Not
   comparable" with the reason, never as a number.

## 7. Decomposition (deck)

Name what the room just saw, fast: paired data and its six encodings,
preparation and eligibility, base model choice, the adapter and its
config, inference serving, evaluation before and after. Then one slide
per other modality on what changes: image is dataset-composition
sensitive, audio lives or dies on pairing and clipping, video pays for
temporal consistency. The training ladder (UI, API, YAML, code, JAX)
in one pass. Merging as the shortcut with sharp edges.

## 8. Notebook practice (standalone Jupyter)

A deliberate switch: leave the board visible on the projector or not,
but open `notebooks/full-session.ipynb` in its own JupyterLab via
`just session-notebook`. This is the pragmatic take-home. Participants
follow the end-to-end material and can load the exact
`chess_sft.jsonl` the room exported. Provider and local-model cells are
optional and presenter-rehearsed; no attendee needs a key. The notebook
refers back to the whiteboard's frozen-hash story instead of repeating
it.

## 9. Close (notebook, then the room)

Restate the four outcomes as questions the room can now answer. Point
at the repo and resources from the notebook's final section. Training
any of these models is expensive, but open models keep matching what
closed models did months ago, and Karpathy's microchat shows the
barrier falling. As compute gets cheaper, specialisation and
customisation may matter more than a ten-point benchmark difference.
Intelligence choice is the point.

## Participation honesty

Assume up to 40 attendees and venue Internet that drops after idle
minutes and demands a captive portal. The core path therefore runs on
the presenter's machine and reviewed local fixtures: no attendee needs
a provider account or API key, and no core segment multiplies one
generation into 40 cloud requests. Text is fully hands-on (own board,
own game, own rows). Image drawing is hands-on when drawings are
persisted and inspected; provider-backed generation is presenter-led
with the pinned local pair already visible. Audio and video are
presenter-led by default; attendees get prediction and comparison
tasks (which take is adapted, which metric regressed) instead of a
pretend hands-on. The run of show marks each segment's mode.

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

## Topic reference per modality

Material available per page when questions go deep. None of it is a
scheduled lecture.

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
