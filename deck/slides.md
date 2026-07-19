---
theme: seriph
title: Same Recipe, Different Results
info: |
  ## Same Recipe, Different Results
  Fine-tuning models across text, image, audio, and video.
  One domain: chess. EuroSciPy 2026 workshop.
class: text-center
colorSchema: dark
drawings:
  persist: false
transition: slide-left
mdc: true
---

<!--
SPEAKER NOTES - OPENING:
TIMING: 90 seconds. Say the board URL now and again on slide 9.
The three assets framing matters: board for the room, deck for the
story, notebook for the take-home. Everything survives the session.
-->

# Same Recipe, Different Results

## Fine-tuning across text, image, audio, video

<div v-click class="mt-8">

One domain: **chess**.

</div>

<div v-click class="mt-6 opacity-70 text-sm">

Three assets, all yours to keep: a whiteboard you will play on,
this deck, and a notebook that contains the whole session.

</div>

<div @click="$slidev.nav.next" class="mt-12 py-1 hover:bg-white hover:bg-opacity-10">
  <div v-click>
    the story first <carbon:arrow-right />
  </div>
</div>

---
transition: fade-out
layout: two-cols
---

# The chess story

<div v-click class="mt-4">

Played as a kid. Forgot about it for years.

</div>

<div v-click class="mt-4">

April: the Duolingo chess pathway.

</div>

<div v-click class="mt-4">

2 matches a day. Then 30. Then 50.

</div>

<div
  v-motion
  :initial="{ scale: 0.6, opacity: 0 }"
  :click-4="{ scale: 1, opacity: 1, transition: { type: 'spring', damping: 12, stiffness: 120 } }"
  class="mt-8 text-4xl font-bold">

1,000+ matches. Elo past 1,000.

</div>

::right::

<div class="img-slot ml-8 mt-12">
  <div class="img-slot-label">image: duolingo-streak.png</div>
  <div class="img-slot-prompt">Hand-drawn calendar with chess pawns marching across the days, one pawn per day growing gradually into a queen, ink sketch, warm accent on the final square</div>
</div>

<!--
TIMING: 2 minutes. This is the personal hook, do not rush it.
The Duolingo mechanic comes back later: start over costs a loss,
which is exactly why the streak worked on me.
-->

---
layout: two-cols
---

# Elo, briefly

<div v-click>

A number that predicts results. 400 points of gap means the
stronger player wins about 9 in 10.

</div>

<div v-click class="mt-4">

Beating the bot *at your level* is genuinely hard. That is the
design: you win about half your games, forever.

</div>

<div v-click class="mt-4 opacity-70">

Keep this in mind when a language model plays. It has no Elo.
It has a training set.

</div>

::right::

<div class="img-slot ml-8 mt-10">
  <div class="img-slot-label">image: elo-ladder.png</div>
  <div class="img-slot-prompt">A ladder drawn in ink where each rung is a chess rating number, small figures climbing, some falling, editorial illustration, off-white paper</div>
</div>

---
layout: center
---

# Rules refresher

<div class="text-left max-w-md mx-auto">

<div v-click>8x8 board. Sixteen pieces each. The goal is the enemy king.</div>

<div v-click class="mt-4">Knights jump. Bishops slide. Pawns dream.</div>

<div v-click class="mt-8 opacity-70">

Not seen *The Queen's Gambit*? Leave now, watch it, come back.
We will still be here.

</div>

</div>

<!--
WARNING: the Queen's Gambit line is a joke. Land it, pause one beat,
move on. Do not explain it.
-->

---

# Chess today

<div v-click>

AI beat the world champion in **1997**. Superhuman engines have been
free for two decades.

</div>

<div v-click class="mt-4">

Chess is more popular than it has ever been. Tournaments, streamers,
a Netflix show, a Duolingo pathway.

</div>

<div
  v-motion
  :initial="{ y: 40, opacity: 0 }"
  :click-3="{ y: 0, opacity: 1, transition: { duration: 600 } }"
  class="mt-10 text-xl">

Automation did not kill the game. It changed who plays, and why.

</div>

<div v-click class="mt-4 opacity-70 text-sm">

Hold that thought until the end. It is the whole argument for
owning your own models.

</div>

---

# Fine-tuning is moulding intelligence

<div class="mt-2 mb-4 opacity-70 text-sm">What changed: adapting beats rebuilding.</div>

````md magic-move {lines: true}
```text
Train a model from scratch
  data:     ~15T tokens
  compute:  months on a cluster
  cost:     tens of millions
  you get:  a base model that knows everything a little
```

```text
Fine-tune a model
  data:     a few thousand pairs        (yours)
  compute:  minutes to hours, one GPU   (yours)
  cost:     single-digit dollars
  you get:  a model that knows YOUR thing well
```
````

<div v-click class="mt-6 text-sm opacity-70">

The stages that got us here: rules, statistics, gradients,
transformers, diffusion. Every stage kept the previous one's lesson.

</div>

<!--
TIMING: 2 minutes. The magic-move does the work: same five lines,
every value shrinks except what you get.
-->

---
layout: center
---

# The recipe

<ModalityGrid />

<!--
Say the mantra out loud: pairs in, adapter out, eval always.
This slide returns at the end. Say it the same way both times.
-->

---

# The plan

<div class="grid grid-cols-4 gap-4 mt-10">

<div v-click class="plan-cell">
  <div class="plan-title">Text</div>
  <div class="plan-sub">the deep tutorial</div>
  <div class="plan-time">35 min</div>
</div>

<div v-click class="plan-cell">
  <div class="plan-title">Image</div>
  <div class="plan-sub">painting our pieces</div>
  <div class="plan-time">15 min</div>
</div>

<div v-click class="plan-cell">
  <div class="plan-title">Audio</div>
  <div class="plan-sub">the board gets sound</div>
  <div class="plan-time">15 min</div>
</div>

<div v-click class="plan-cell">
  <div class="plan-title">Video</div>
  <div class="plan-sub">the real-world twin</div>
  <div class="plan-time">15 min</div>
</div>

</div>

<div v-click class="mt-10 text-center opacity-70">

Text goes deep so the other three can go fast. It is the same
recipe every time; only the pairs change.

</div>

---

# How to follow along

<div class="mt-4">

1. Open the board URL on the screen
2. Enter your name, land in your workspace
3. Move pieces. Watch the dataset build itself
4. Run jobs. Check evals. Reveal artifacts

</div>

<div v-click class="mt-8 p-4 rounded-lg border border-gray-700 bg-gray-900 bg-opacity-40">

The board is a shared canvas. Your workspace is yours; everyone
else's is read-only. If anything breaks: reload. Your game and your
data survive.

</div>

<!--
NOTE: this is where everyone opens the app. Budget 90 seconds of
dead air and walk the room. The join flow is one text box.
-->

---
layout: center
---

# The room, live

<LiveRoom />

<div class="mt-4 text-center text-sm opacity-60">

Every match, every clock, every sample. This panel is calling the
same API your workspaces use.

</div>

<!--
DEMO PREP: backend must be running (just start). The component polls
GET /presenter/games every 3 seconds and shows a terse offline hint
if the backend is down.
-->

---
layout: section
---

# Building a Chess Machine

## Text. The deep tutorial.

<!--
TIMING: the next six slides carry ~12 minutes of talking,
interleaved with app time on the chess-machine page.
-->

---
layout: center
---

# One move, six datasets

<DatasetShapes />

<div v-click class="mt-4 text-center text-sm opacity-70">

Encoding is a design decision. Each shape trains a different animal.

</div>

---

# From prompt to chat template

````md magic-move {lines: true}
```python {*|1-4|6-7|all}
PROMPT_TEMPLATE = """You are a chess engine assistant.

Position (FEN): {fen}
Legal moves (UCI): {legal_moves}

Return exactly one move from the legal moves list.
Respond with JSON: {{"move": "<uci>"}}"""
```

```python {*|3-6|8-9|all}
# The same intent, shaped for training
CHAT_TEMPLATE = """{% for m in messages %}
<start_of_turn>{{ m.role }}
{{ m.content }}<end_of_turn>
{% endfor %}
<start_of_turn>model
"""

# prompt/completion pairs render through this
# so the model learns where turns begin and end
```

```text {*|2|3|4|all}
<start_of_turn>user
Position (FEN): rnbqkbnr/pppppppp/8/8/...
Legal moves (UCI): e2e4, d2d4, g1f3, ...
Return exactly one move...<end_of_turn>
<start_of_turn>model
{"move": "e2e4"}<end_of_turn>
```
````

<!--
Three steps: the raw prompt, the Jinja template, the rendered turn.
The tokenizer sees the third one. Most fine-tuning bugs live between
step one and step three.
-->

---
layout: center
---

# The reward function

<RewardMeter />

---

# The opponent

<div v-click>

The model plays through the **same environment** you do: timed match,
five minutes, quitting costs a loss.

</div>

<div v-click class="mt-4">

An illegal reply is recorded with reward **-1** and the board does
not move. The environment catches the model. That is the RL lesson,
live.

</div>

<div v-click class="mt-8 p-4 rounded-lg border border-amber-700 border-opacity-40 bg-amber-900 bg-opacity-10">

The two-game beat: five minutes against <strong>small Gemma</strong>,
five against a <strong>frontier model</strong>. Same board, same
recipe, visibly different results.

</div>

<!--
DEMO PREP: OPPONENT_MODELS env set, picker shows both models.
If the model plays an illegal move during the demo: celebrate.
That is the slide happening in front of them.
-->

---

# Evals before training

<div class="mt-6">

| metric | needs | cost |
| --- | --- | --- |
| legal move rate | python-chess | free |
| valid JSON rate | a parser | free |
| centipawn loss | Stockfish | a download |
| mate-in-one accuracy | Stockfish | a download |
| explanation quality | a judge model | cents |

</div>

<div v-click class="mt-6 text-lg">

Evals are the first cell you write, not the last.

</div>

<div v-click class="mt-2 opacity-70 text-sm">

If you cannot measure "better", you cannot claim the fine-tune
helped. You can only claim it ran.

</div>

---

# The training ladder

<div class="mb-2 opacity-70 text-sm">Five rungs. Same dataset every time. Watch the same run change costume:</div>

````md magic-move {lines: true}
```python {*|1-3|5-7|all}
# Rung 4: code that reads like config (Unsloth)
from unsloth import FastModel
from trl import SFTConfig, SFTTrainer

model, tok = FastModel.from_pretrained(
    "unsloth/gemma-4-E2B-it", load_in_4bit=True)
model = FastModel.get_peft_model(model, r=8, lora_alpha=8)
```

```yaml {*|1-2|4-8|all}
# Rung 3: the run is a file (axolotl)
base_model: google/gemma-4-E2B-it

adapter: lora
lora_r: 16
chat_template: gemma4
datasets:
  - path: data/processed/text/chess_sft.jsonl
```

```python {*|1-2|4-7|all}
# Rung 5: no trainer, no config, just the loss (JAX)
import optax; from flax import nnx

def loss_fn(model, batch):
    logits = model(batch["tokens"])
    return optax.softmax_cross_entropy_with_integer_labels(
        logits, batch["targets"]).mean()
```

```text {*|2|3|4|5|6|all}
The whole ladder:
  1. UI       Unsloth Studio: no code, live loss curves
  2. API      a training endpoint: your data leaves the room
  3. config   axolotl: the run is a YAML file
  4. code     Unsloth: five lines, one GPU
  5. loss     JAX: it trains live in the notebook, on CPU
```
````

<!--
TIMING: 4 minutes. The magic-move carries it: same run, different
costume at every rung. Rung 5 actually executes in the notebook.
-->

---
layout: section
---

# Painting Our Pieces

## Image. Same recipe, new pairs.

---
layout: two-cols
---

# Image pairs

<div v-click>

The pairs are **(image, caption)** now. Twenty photos of your chess
set, captions that always contain a trigger word.

</div>

<div v-click class="mt-4">

DreamBooth-style LoRA: the model learns *your* pieces the way it
learned everything else. The trigger word is the handle.

</div>

<div v-click class="mt-4 opacity-70 text-sm">

On the board: generate with FLUX.2 Klein, then swap in your adapter
and generate again. Same prompt, your pieces.

</div>

::right::

<div class="img-slot ml-8 mt-10">
  <div class="img-slot-label">image: four-boards.png</div>
  <div class="img-slot-prompt">Four small chess boards in a row, each drawn in a different medium: pencil text, oil paint, sound waves, film strip, unified ink style</div>
</div>

---

# VLM as judge

<div v-click>

The eval problem: "does this look like my knight" has no
python-chess. Rules cannot grade style.

</div>

<div v-click class="mt-4">

So a vision model grades it: piece identity, style adherence, board
coherence. Rubric in, scores out. Costs cents.

</div>

<div v-click class="mt-8">

```python
messages = [{"role": "user", "content": [
    {"type": "image_url", "image_url": {"url": generated}},
    {"type": "text", "text": "Score 1-5: is this a knight, "
        "in the reference style? JSON: {identity, style}"}]}]
```

</div>

<div v-click class="mt-4 opacity-70 text-sm">

A judge model is an eval you can afford before you can afford
human raters. It is also a bias you should know you bought.

</div>

---
layout: section
---

# Giving the Board Sound

## Audio. Local models this time.

<!--
TIMING: audio and video are 15 minutes each. The recipe repeats,
so the slides get lighter; the app carries the demos.
-->

---

# Audio pairs, local weights

<div v-click>

Pairs: **(text, audio)**. "wooden piece landing on wood, short
knock" and two seconds of exactly that.

</div>

<div v-click class="mt-4">

Runs on the presenter GPU: **musicgen-small** (0.6B) and
**stable-audio-open**. No API key, no queue, your fans spin.

</div>

<div v-click class="mt-6">

```python
# or skip the model and make the sound yourself
t = np.linspace(0, 0.05, int(0.05 * 44100))
click = np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 90)
```

</div>

<div v-click class="mt-4 opacity-70 text-sm">

The synth click is the audio equivalent of the reward function:
small enough to understand completely.

</div>

---

# Audio evals

<div class="mt-6">

| metric | how |
| --- | --- |
| duration matches request | read the file header |
| clipping | count samples at the rails |
| spectral sanity | look at the spectrogram |
| "sounds like a chess clock" | human ears, still cheapest |

</div>

<div v-click class="mt-6 opacity-70">

Computed from real bytes, not vibes. The notebook does all four on
the click it just synthesized.

</div>

---
layout: section
---

# Video of the Real-World Use Case

## The costs get real.

---

# Video pairs, real money

<div v-click>

Pairs: **(video, caption)**. The knight fork, three seconds,
labeled.

</div>

<div v-click class="mt-4">

On the board: LTX fast, about a minute for six seconds. Veo in the
picker for the frontier comparison.

</div>

<div v-click class="mt-8">

| | image | video |
| --- | --- | --- |
| per generation | fractions of a cent | **cents per second** |
| eval dimensions | identity, style | + motion, flicker, physics |

</div>

<div v-click class="mt-6 text-lg">

Say the numbers out loud. Video is where hobby budgets meet reality.

</div>

---

# Merging, and when it wrecks

<div v-click>

Two adapters, one model. A YAML file and ten minutes:

</div>

<div v-click class="mt-4">

```yaml
merge_method: slerp
models:
  - model: gemma-4-chess-moves
  - model: gemma-4-chess-commentary
parameters:
  t: 0.5
```

</div>

<div v-click class="mt-6">

Sometimes you get both skills. Sometimes you get neither, plus a
model that hallucinates knights.

</div>

<div v-click class="mt-2 opacity-70 text-sm">

The fix is the same as everywhere else in this session: eval before
you believe.

</div>

---
layout: center
---

# Same recipe, four times

<ModalityGrid :stagger="350" />

<!--
The mantra, second and last time: pairs in, adapter out, eval always.
Same words as slide 7.
-->

---

# The economics

<div v-click>

An adapter is megabytes. A fine-tune is dollars. A GPU-hour is
pocket money.

</div>

<div v-click class="mt-4">

Owning the weights means: no per-token bill on your own domain, no
deprecation on someone else's schedule, no terms-of-service between
you and your data.

</div>

<div v-click class="mt-8 p-4 rounded-lg border border-gray-700 bg-gray-900 bg-opacity-40">

The barrier keeps dropping. Karpathy's microchat trains a working
GPT in a few hundred lines. You watched a transformer train inside
a notebook cell today.

</div>

---
layout: two-cols
---

# Your personalised instructor

<div v-click>

The point was never the chess engine. Stockfish exists and is free.

</div>

<div v-click class="mt-4">

The point is a model that teaches chess **the way you want to
learn it**. Mine: win while capturing as few pieces as possible.

</div>

<div v-click class="mt-4">

Nobody sells that model. That is exactly why you can build it.

</div>

::right::

<div class="img-slot ml-8 mt-10">
  <div class="img-slot-label">image: instructor.png</div>
  <div class="img-slot-prompt">A friendly robot tutor leaning over a chess board across from a human, pointing at a knight, warm hand-drawn editorial style</div>
</div>

<!--
TIMING: 90 seconds. This is the emotional close; the resources slide
after it is the practical one.
-->

---
layout: center
---

# Take it home

<div class="text-left max-w-lg mx-auto mt-4">

- **The repo**: board, deck, notebook, all of it
- **The notebook**: `just session-notebook`
- **Your dataset**: the export button was real; the file is yours
- Unsloth, axolotl, mergekit, verifiers, and fal: linked in the notebook

</div>

<div v-click class="mt-10 text-2xl">

Pairs in. Adapter out. Eval always.

</div>

<div v-click class="mt-6 opacity-70">

Thank you.

</div>

<!--
Leave this slide up during Q&A. The mantra is the summary.
-->
