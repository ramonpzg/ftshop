# Session plan

Same Recipe, Different Results: Fine-Tuning Models Across Modalities.
EuroSciPy 2026, 90 minutes. One shared domain: chess. Four modalities:
text, image, audio, video.

This is the working plan for the session itself. For the minute-by-minute
app walkthrough, see [demo-plan.md](demo-plan.md). For how the app is put
together, see [architecture.md](architecture.md).

## Why this session

Fine-tuning is moulding intelligence. It gives shape to a future where we
interact with AIs of all sorts of personalities, skills, and aptitudes,
all while keeping a general level of intelligence far above the average
human and fitting in the devices we already own.

For that to happen we need mediums that expose the flexibility of a
model's internals while giving its complexity more layers than a
croissant. Depending on what someone needs, they chew as much of the
mechanics of fine-tuning as they want. To be fair, the $20 a month we pay
today is not bad at all. The point is not to drop those services. The
point is that we can also have our own AI.

## Delivery setup

The app is a local-first tldraw whiteboard. Options for the room, in
order of preference:

1. Presenter hosts one copy, binds it to the local network, and shares
   the URL over the venue wi-fi. This is what `just start` supports today.
2. A hosted copy on Fly.io or similar as a fallback, so a copy is always
   reachable and the presenter's laptop is just another client.
3. Everyone runs the app on their own device and follows along locally.
   Slowest to set up, but immune to bad wi-fi.
4. tldraw sync for true shared-canvas collaboration. Deferred past v0,
   but the state model is already shaped for it.

As someone joins they enter their name, get an ID, and the app creates a
workspace for them: a chess board, a dataset panel, a mini IDE, a config
panel, an artifact panel, and an eval panel. As they play, the dataset
builds on screen as JSON. Presenter controls pull everyone to a section
and send them back to their workspaces.

## Page 1: Presentation

- The stages that got us to today's transformer and diffusion based
  generative models.
- How the session runs, and the repo with the code.
- Fine-tuning as moulding intelligence to your will.
- The chess story. I played as a kid, then rediscovered the game through
  Duolingo's chess pathway in April. Two matches a day became thirty,
  fifty on the hardcore days. Over a thousand matches later my elo
  passed 1000.
- What elo actually is.
- The rules, quickly, in case someone has never played.
- The Queen's Gambit check. Anyone who has not watched it should leave
  and come back when they finish it. They have been missing out.
- AI has beaten grandmasters for years, yet chess is more popular than
  ever. Tournaments around the world, big and small. What a pro can earn.
- Applications of chess beyond the board.
- The beauty of fine-tuning here: we can each build our own personalised
  instructor. Mine would teach me to win while capturing as few of my
  opponent's pieces as possible.

## Page 2: Building a Chess Machine (text)

The main tutorial. The other three pages run faster and lean on this one.

Attendees play a game first. Their moves get recorded live and shown as
dataset rows next to the board. That data, plus freely available data
(Stockfish-derived sets, plenty already on Hugging Face), is the training
story for the session.

A plain chess engine is a solved problem. The interesting dataset is the
one that relates each game to scenarios at work, at home, in sports, in
day-to-day life. A fast LLM behind an API can build that link as the game
progresses. About a hundred terse, direct examples of finished games
mapped to real-world scenarios is enough.

Topics, in rough order:

- Data formats. PGN prefix to next move, FEN to move, FEN plus legal
  moves to move, board tensor to move class, policy and value labels,
  RL trajectories.
- SFT teaches the model what good answers look like. RL teaches the
  model what good actions do. Chess is a good RL environment because the
  environment can validate every move.
- Handling illegal moves. Easier at the app level than the model level,
  but you want both.
- What Stockfish is and where it fits.
- Prompt and chat templates, including Jinja.
- Model choice. Base or RL'd checkpoint. One player model or a player
  plus an analyst with tool access.
- The training ladder, from most to least abstracted: a UI like Unsloth,
  a training API (Thinking Machines has a good one), a config file like
  Axolotl, code that reads like config (Unsloth, PEFT), and as low level
  as it gets (JAX, which reads closer to NumPy than PyTorch does).
- LoRA vs QLoRA vs full fine-tuning.
- Picking hardware. Which GPU class, from where.
- Optional stretch: next-move prediction that takes a PNG of the board,
  as a bridge to the image page.

## Page 3: Painting Our Pieces (image)

Everyone draws their favourite pieces. Those drawings become the dataset
for a model that produces hand-drawn chess pieces and boards in a
specific style based on the plays passed to it. I could not find an
existing example of this use case, so it is unique to the session.

- What changes from text: templates, data prep, and sensitivity to
  dataset size and composition.
- Diffusion vs transformers for generation, and the fact that text
  diffusion transformers now exist.
- What providers quietly do to your prompts before generation.
- Data preparation is the whole game: captions, objects, trigger words,
  aspect ratios, output dimensions.
- The approach taxonomy, with an example of each: text to image, image
  to image, image plus text to image, text to SVG, image to SVG, image
  editing, image layering.
- The code ladder again: UI, then stablediffusion.cpp, then Diffusers.
- Candidate model: Flux 2 Klein 4B.
- Why models struggle to write text on images, and Ideogram's open
  model as the current reference point for it.
- Where this is heading: Google's Genie line and world models.

## Page 4: Giving the Board Sound (audio)

- What audio covers: music, birds chirping, alarms, text to speech,
  speech to text, translation, real-time voice bots.
- Chess ideas: music that intensifies as the game sharpens, capture
  sounds, an illegal-move sound, a real-time narrator doing "let's get
  ready to rumble".
- Sound is vibration in air, audio is its representation, and a
  spectrogram turns it into something you can treat like an image.
- Mechanics of a transformer-based audio model.
- Reusable material: the PyData NYC talk, the Qdrant music fine-tuning
  tutorials with wav2vec genre classification, panns-inference for
  embeddings.

## Page 5: Video of the Real-World Use Case (video)

For each game, Luna first writes a detailed real-world case and a filmable
scene prompt. The prompt covers one setting, visible characters, a physical
sequence of actions, camera movement, lighting, and sound. It does not ask the
video model to move chess pieces. Take a hundred of those prompts from page 2,
generate ten to fifteen second clips with one or several top video models, and
use those to fine-tune a recent LTX model. This page stays light and leans on
an online training setup.

- Mechanics of a video model: frame sampling, temporal consistency,
  and compute that escalates faster than you expect.
- The same recipe applies: LoRA or full fine-tuning, same shape,
  different failure modes.

## Closing thoughts

Training any of these models is expensive. We are lucky that open models
match or pass what closed models did two years, even six months, ago. It
is not unrealistic for the economics of training to change how models
get released. It is also not unrealistic for the barrier to entry to
keep dropping. Karpathy's microchat, a few hundred lines that train a
GPT on consumer hardware, is a vivid example.

As compute gets cheaper, specialisation and customisation may matter
more than a ten-point benchmark difference. I welcome a future with
intelligence choice.

Resources go here before the session.

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
