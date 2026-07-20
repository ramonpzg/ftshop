# Deck plan

The Slidev deck is one of the workshop's three assets: the board is
where the room works, the deck is where the narrative lives, the
standalone Jupyter notebook is pragmatic working material and the
take-home. This plan follows the
polyglot workflow: every slide gets its content, layout, and
animation noted before it gets built; images get a prompt for an
image model; components get built alongside their slides in bouts.

Working agreements, carried over from polyglot and this repo:

- Writing style: terse, direct, pragmatic. No emojis, no em dashes,
  no marketing fluff. Speaker notes in HTML comments with TIMING and
  WARNING annotations.
- Animations matter: magic-move for code evolution, v-motion with
  spring physics for hero moments, v-click for pacing, v-mark for
  annotations. Never animation for its own sake; every motion makes
  a point about the content.
- Components: Vue script setup, dark glassy panels, staged reveals,
  graceful offline states. Where a component can talk to the running
  FastAPI backend, it should, with a clean fallback when the backend
  is down.
- The session plan is the narrative source of truth. Phase 34's run of
  show (docs/demo-plan.md) uses the deck in two passes rather than
  end to end: slides 1-11 carry the opening (motivation, chess
  grounding, the map and the mantra), slides 12-17 and 19-24 carry the
  post-demo decomposition, and the close happens from the notebook, so
  slides 25-28 are reference material rather than a scheduled return.
  The slide order below still records v1's sequence; physically
  reordering and rewording slides is phase 35's job, and the two-pass
  mapping works on the current order without it.

Build in bouts of five slides. v1 status is tracked per slide.

## Components

| Component | What it does | Backend |
|---|---|---|
| `LiveRoom.vue` | The room right now: playing/finished/samples totals and per-game countdowns, polled every 3s | GET /presenter/games |
| `DatasetShapes.vue` | One move (e4) cycling through the six dataset encodings with eased morph transitions | none |
| `RewardMeter.vue` | Interactive reward function: click an outcome, watch the reward land and the total move | none |
| `ModalityGrid.vue` | The recipe, four times: pairs in, adapter out, eval always, staggered reveal per modality | none |

## Image prompts

Placeholders in v1 are styled blocks carrying their prompt. Generate
with FLUX.2 or similar, hand-drawn/editorial style, monochrome-ish to
sit near the tldraw aesthetic:

1. `cover-board.png`: "Minimalist hand-drawn chess board viewed at a
   low angle, single knight casting a long shadow shaped like a neural
   network graph, ink on paper, high contrast, off-white background"
2. `duolingo-streak.png`: "Hand-drawn calendar with chess pawns
   marching across the days, one pawn per day growing gradually into
   a queen, ink sketch, warm accent on the final square"
3. `elo-ladder.png`: "A ladder drawn in ink where each rung is a chess
   rating number, small figures climbing, some falling, editorial
   illustration, off-white paper"
4. `four-boards.png`: "Four small chess boards in a row, each drawn in
   a different medium: pencil text, oil paint, sound waves, film
   strip, unified ink style"
5. `instructor.png`: "A friendly robot tutor leaning over a chess
   board across from a human, pointing at a knight, warm hand-drawn
   editorial style"

## The slides

Timing target: the deck carries about 25 minutes of talking total,
interleaved with app time. 90 minutes overall.

### Bout 1: opening (slides 1-6)

1. **Title.** "Same Recipe, Different Results." Subtitle: fine-tuning
   across text, image, audio, video. One domain: chess. Layout:
   cover, image cover-board right. v-click reveals the three assets
   line: a whiteboard, a deck, a Jupyter notebook. NOTE: state the URL of the
   board early and twice.
2. **The chess story.** Duolingo chess pathway, 2 matches a day, then
   30, then 50, over 1000 matches, Elo past 1000. v-motion counter
   easing up from 2 to 1000+. Image duolingo-streak. TIMING: 2 min,
   this is the personal hook, do not rush it.
3. **Elo, briefly.** What the number means, why beating the bot at
   your level is hard. Image elo-ladder. Two v-clicks max.
4. **Rules refresher.** The board, the pieces, the goal. The Queen's
   Gambit check: not seen it? Leave, watch it, come back. WARNING:
   this is a joke, land it and move on.
5. **Chess today.** AI beat grandmasters years ago; chess is more
   popular than ever. The point: automation did not kill the game,
   it changed who plays and why. Sets up "intelligence you own".
6. **Fine-tuning is moulding intelligence.** The stages that got us
   here, compressed: rules, statistics, gradients, transformers,
   diffusion. Why adapt a model instead of training one. magic-move
   of a two-line "train from scratch" cost table into a "fine-tune"
   one.

### Bout 2: the recipe and the room (slides 7-11)

7. **The recipe.** The mantra slide: pairs in, adapter out, eval
   always. ModalityGrid component, staggered reveal. This slide
   returns at the end; say the mantra out loud both times.
8. **The plan.** Four modalities, one domain. Text is the deep
   tutorial; image, audio, video run faster. Simple grid, v-clicks.
9. **How to follow along.** The app: join with your name, move
   pieces, watch the dataset build, run jobs, check evals. Screenshot
   or live iframe of the board. NOTE: this is where everyone opens
   the app; budget dead air.
10. **The room, live.** LiveRoom component against the running
    backend. Everyone's game on one slide. DEMO PREP: backend must be
    up; component shows a terse offline hint otherwise.
11. **SECTION: Building a Chess Machine.** Section layout, text page
    of the app on screen after this.

### Bout 3: text deep dive (slides 12-17)

12. **One move, six datasets.** DatasetShapes component cycling e4
    through pgn-prefix, fen, fen+legal, tensor, policy/value, RL
    trajectory. The point: encoding is a design decision, not a
    given.
13. **Prompt to chat template.** magic-move: raw prompt string, then
    the Jinja chat template, then the tokenized turn structure. lines
    on, three steps.
14. **The reward function.** RewardMeter component. Click illegal:
    -1. Click mate: +10. The RL environment is five lines of Python
    and a chess library that knows the rules.
15. **The opponent.** The model plays through the same environment:
    timed match, quit costs a loss, illegal replies score -1 and do
    not move the board. Two-model beat: small Gemma, then a frontier
    model. Same recipe, different results, live on the board.
16. **Evals before training.** Legal move rate, valid JSON rate, then
    the heavier ones: centipawn loss, mate-in-one. Evals are the
    first cell you write, not the last.
17. **The training ladder.** Five rungs, most to least abstracted:
    Studio UI, API, axolotl YAML, Unsloth code, raw JAX. magic-move
    across the actual code: unsloth block morphs into axolotl YAML
    morphs into the JAX loss loop. TIMING: 4 min, the magic-move
    carries it.

### Bout 4: the other modalities (slides 18-24)

18. **SECTION: Painting Our Pieces.** Image four-boards teased here.
19. **Image pairs.** (image, caption) rows; DreamBooth-style LoRA;
    trigger words. Generation on the board via FLUX.
20. **VLM as judge.** The eval problem for images; a vision model
    grades piece identity and style adherence. Costs cents.
21. **SECTION: Giving the Board Sound.** Audio pairs: (text, audio).
    Local models on a laptop GPU: musicgen-small, stable-audio-open.
    The click synth: you can also just make the sound yourself.
22. **Audio evals.** Duration, clipping, spectrogram sanity. Computed
    from real bytes, not vibes.
23. **SECTION: Video of the Real-World Use Case.** Luna turns a game
    into a detailed filmable situation. LTX fast or Veo stages that
    situation, not a chess move. The cost table is real now: cents per
    second. Say the numbers out loud.
24. **Merging.** Two adapters, one model: slerp in a YAML file. And
    when merging wrecks both. mergekit config on screen.

### Bout 5: closing (slides 25-28)

25. **Same recipe, four times.** ModalityGrid returns, all four rows
    filled. The mantra again.
26. **Economics.** What owning the weights buys: no per-token bill on
    your own domain, no deprecation on someone else's schedule.
    Karpathy microchat: the barrier keeps dropping.
27. **Your personalised instructor.** The point of the whole session:
    a model that teaches chess the way you want to learn it. Mine:
    win while capturing as few pieces as possible. Image instructor.
28. **Resources.** The repo, the Jupyter notebook, verifiers, Unsloth,
    axolotl, mergekit, and fal. QR to the repo. Thanks.

## v1 status

Built: all 28 slides, all four components, image placeholders with
prompts inline. Not yet: real images, the live iframe on slide 9,
timing rehearsal.
