# Handover: phase 31, the deck joins the board and the notebook

Written 2026-07-07, from Ramon's three-assets framing: the tldraw
board is where the room works, the Slidev deck is where the narrative
lives, the marimo notebook is the fallback and the take-home. This
phase built the deck v1 and wired all three together.

## What was built

**The plan first.** docs/deck-plan.md follows the polyglot workflow
(ramonpzg/polyglot, branch deck-polish-1, reviewed before building):
every slide has its content, layout, and animation noted; images get
prompts for an image model; components get listed with their backend
wiring. Bouts of five slides. The plan is the contract; slides.md is
its implementation.

**The deck, v1.** deck/ is a Slidev project (@slidev/cli ^52, theme
seriph, dark colorSchema, @vueuse/motion). 28 slides covering the
whole session arc: story, Elo, the recipe mantra, the room live, the
text deep dive, image/audio/video, merging, economics, the
personalised instructor close. Patterns lifted from polyglot and
tightened:

- magic-move with lines and per-step highlights, three times: the
  scratch-vs-finetune cost table, prompt to chat template to rendered
  turn, and the training ladder (Unsloth to axolotl YAML to JAX loss
  to the five-rung summary).
- v-motion spring physics for the two hero numbers (1,000+ matches,
  the fine-tune cost collapse); v-click everywhere for pacing;
  speaker notes with TIMING / WARNING / DEMO PREP, same convention
  as polyglot.
- Image placeholders are styled blocks carrying their generation
  prompt inline, so the deck presents cleanly before the images
  exist and the prompts travel with the slide.

**Four components,** in the polyglot glassy style but with one accent
(amber) instead of a palette per concept:

- LiveRoom.vue polls GET /presenter/games every 3s: totals plus
  per-game countdowns ticking client-side between polls. Terse
  offline hint when the backend is down.
- DatasetShapes.vue cycles 1. e4 through the six dataset encodings
  with eased morphs, pausable on hover, dot navigation.
- RewardMeter.vue: click an outcome, the reward pops with a spring,
  the return accumulates, a chip trail remembers. compute_reward as
  a toy you can feel.
- ModalityGrid.vue: the recipe table with staggered row reveal and
  the mantra landing last. Used twice (slide 7 and 25), second time
  with a faster stagger.

**The board embeds the deck.** New deck-panel shape (DeckShapeUtil +
DeckPanel): an iframe to the Slidev server, URL editable per browser
(localStorage), Open link for the real tab where presenter mode
lives. `ensureDeckShape` runs on every mount, not only fresh seeds,
so existing canvases grow the panel below the slide-sketch row at
(0, 2450). Verified live: panel seeds, iframe loads the deck.

**The notebook's readable twin.** `just notebook-md` runs
`marimo export md` to produce notebooks/full-session.md (checked in),
so the whole session is also a markdown file for people who want to
read before they run.

**Justfile:** `just deck`, `just notebook-md`, and `just install` now
installs deck dependencies too.

## Intentionally deferred, and why

- **Real images.** The five prompts are written and travel with
  their slides; generating and art-directing them is Ramon's call.
- **A live board iframe on slide 9.** The screenshot placeholder
  stands in; embedding the app inside the deck inside the app is a
  hall of mirrors best entered deliberately.
- **Slide count vs the seeded tldraw sketches.** The Presentation
  page's 11 sketch frames stay as the storyboard; the deck is the
  presentation. They agree on content but are not generated from
  each other.
- **No deck tests.** Slidev builds are the check (`bun run build`
  passes); component logic is simple enough that a test harness for
  the deck would outweigh it.

## Known issues / tech debt

- The polyglot review lives in this handover only; the repo clone
  under /workspace/polyglot is session-local and gone tomorrow.
- Slidev's seriph theme fetches Google fonts at runtime; offline at
  the venue means fallback fonts. Acceptable; self-hosting fonts in
  the deck is an hour if it ever matters.
- LiveRoom hardcodes localhost:8000 as its default apiBase prop; a
  LAN-served deck viewed from another machine would need the prop
  changed in slides.md (single call site).
- notebooks/full-session.md is generated; editing it by hand loses
  work on the next `just notebook-md`. The header comment in the
  notebook says so.

## What the next phase should tackle first

1. Generate the five images from their prompts, drop them in
   deck/images/, replace the placeholder blocks.
2. A timing rehearsal against the deck: the plan claims ~25 minutes
   of deck talking inside the 90; measure it.
3. The standing item, one more phase older: real keys, real
   rehearsal.

## Gotchas

- Slidev headmatter belongs to slide 1: `class: text-center` there
  styles the title slide, not the deck. Per-slide frontmatter blocks
  separate slides; a stray `---` splits a slide in half.
- magic-move blocks use four backticks outside, three inside. An
  editor that trims trailing whitespace inside them is fine; one
  that collapses the fence breaks the slide.
- The deck panel's iframe is cross-origin (5173 vs 3030), so the
  board cannot probe whether the deck is up the way the notebook
  panel probes its same-origin WASM build. The header hint ("Blank?
  Run: just deck") does the job a probe would.
- First visit to the Slidev dev server compiles every slide; a
  screenshot 2.5s after page one loads black. Warm it before
  presenting from it, or use the built version.
- The deck dev server and `slidev build` share port and cache
  peacefully, but two dev servers on 3030 do not: the second exits
  with EADDRINUSE, which is how one load-bearing background server
  masqueraded as a build failure during verification.
