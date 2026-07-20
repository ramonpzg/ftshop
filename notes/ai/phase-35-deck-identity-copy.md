# Phase 35 handover: deck identity and copy

**Status: phase 34 integration pending. This phase is incomplete.**

Phase 35 ran in parallel with phase 34 under the two-stage workflow in
`notes/comms/p4-deck-identity-copy.md`. This branch contains the
complete deck foundation, revised through three review rounds with
Ramon; every repository-wide obligation waits for the accepted phase
34 result. The branch must not merge before the integration stage
below is done and all acceptance checks are repeated.

## What was built

### Design system (docs/deck-plan.md, deck/style.css)

A scoresheet-derived paper/ink system: `--paper` ground, `--ink` text,
one functional accent (`--accent`, pen blue), semantic `--good`/`--bad`
greens and reds, hairline `--rule` borders, 2px corner radii, one
component surface treatment. IBM Plex Sans and Mono self-hosted through
Fontsource packages (OFL 1.1); `fonts.provider: none` in the headmatter
so nothing fetches Google Fonts at presentation time. Fixed title,
content, and footer geometry; `global-bottom.vue` renders the footer
(z-indexed above the layout's opaque ground) with a `footer: false`
frontmatter opt-out. Shiki pinned to `github-light` in
`deck/setup/shiki.ts`: the default palette was unreadable on paper and
vitesse-light, tried first, is too muted for a washed-out projector.
Code-first slides carry a `code-lg` class that raises code to 1rem.

### Slides and routes (deck/slides.md, slides-full.md, slides/01..05)

47 slides in the exact PLAN_V2 sequence across five section files; the
title slide is slide 1 of `01-origin.md` so both entries share it.
The TUI outcome deliberately precedes the chess recap.

Two entry files encode the two routes:

- `slides.md` is the default route: its `src` ranges exclude exactly
  the four OPTIONAL slides (Oscar, mappings two and three, the model
  tree), giving 43 slides and a 24:50 opening measured from the notes.
- `slides-full.md` imports everything for rehearsal
  (`bun run dev:full`, `bun run build:full`).
- `tests/route.test.ts` keeps the ranges honest against the OPTIONAL
  markers in the speaker notes, so the routes cannot drift.

Every slide carries the TIMING/SAY/CLICK/SOURCE/CUT/FALLBACK note
contract, enforced by test. The default-route budget, optional adds,
and mid-deck cut order live in `docs/deck-plan.md`.

### Components (deck/components, deck/lib)

All educational progression is presenter-controlled. Components take a
`clicks` prop from the slide and derive their visible state through
pure functions in `deck/lib/clicks.ts`, so backward/forward navigation
restores exact frames and bun tests drive every state without a DOM.

- `DatasetShapes`: rail-and-panel stepper over six encodings from
  `lib/datasetShapes.ts`. Every payload is strictly valid JSON with
  real FENs; truncation is stated in the caption; a test JSON.parses
  all six. Phase 33 values hold (`3980` = e2e4, policy_move_reward).
- `ModalityGrid`: click-revealed recipe rows, no timers.
- `NotationMorph` + `ChessBoard`: one real position (Ruy Lopez after
  2...Nc6), the same move as FEN/UCI/SAN/PGN, board fixed, from/to
  squares accent-highlighted. `lib/chess.ts` parses FEN; its tests
  caught an inverted square parity and a wrong hand-written FEN.
- `DataUniverse`: five data circles plus the train/eval split, with
  paper-halo labels.
- `OutcomeCompare`: matched input, BASE/ADAPTED columns, metrics per
  the phase 34 contract (model_legal_move_rate, valid_json_rate,
  explanation_rate) with the trade direction encoded: explanations
  drop on the adapted checkpoint, by design. Values are placeholders.
- `CostAtTarget`: seven columns matching the claimed comparison:
  modality, task and target, local setup with amortisation basis,
  local and API marginal per-request cost, volume assumption, and
  threshold attainment, plus a path-identity line under the table.
  All values `[SOURCE, DATE]`/PENDING; real numbers slot in without
  redesign.
- `RewardMeter`: presenter-pressed outcomes; environment feedback
  separated from model output; the slide states the phase 33 fallback
  semantics for illegal model replies.
- `PhoneTuiReplay`: phone-framed local video, poster, native controls
  (seek, restart, volume), `object-fit: contain` so the recording is
  never cropped, 340px frame.
- `MediaFrame`: fixed-geometry frame for every asset; missing files
  render the expected file name, content, and ratio in place. A
  `height` prop caps portrait media so phones cannot cross titles or
  footers; audio renders as a compact control strip.
- `LiveRoom`: phase 32 state machine and polling untouched; chip per
  phase: LIVE, CONNECTING, RECONNECTING, OFFLINE (reserved for
  unavailable). All four states verified against a running backend.

The A/B answer on each which-was-adapted slide is a `<details>`
disclosure opened by mouse only: the clicker cannot leak it, and the
default is to hold answers for the combined reveal table.

### Copy

Full tone pass on deck copy and speaker notes. Banter and puns are
gone; protected V2 beats stay as named placeholders: dog-thinking
meme, "what could possibly go wrong", "Cool bruh" with the cookie GIF,
goth Minions, the corporate-lamp paragraph, the Queen's Gambit beat,
and "sassy as fuck" in the slide 8 SAY note (Ramon's delivery line,
speaker-facing only). Truthfulness rules hold: Luna is always the
scenario writer; model illegal replies are labelled fallbacks landing
in model_legal_move_rate; the interventions slide says the adapted
model "learns how to choose"; the Gemma 4 chat-template slide renders
through `AutoProcessor.apply_chat_template` and shows `<bos>` plus the
`<|turn>`/`<turn|>` markers rather than handwritten syntax; the
training-ladder frames are labelled abbreviated implementation shapes;
the merge slide shows a valid mergekit slerp config (base_model,
slices, dtype) over two full checkpoints and the SAY note routes
adapter-level merging to PEFT.

### Checks (deck/tests, deck-local commands)

- `bun test`: the deck suite covers copy rules (em dashes, emoji with
  the chess-glyph block exempt, stock phrases, narrow allowlist), the
  speaker-note contract, the placeholder inventory cross-check,
  deterministic progression and reverse navigation, JSON validity and
  fit budgets, the default-route encoding, and the
  prefers-reduced-motion CSS block (durations collapsed with
  !important, delays zeroed, universal including pseudo elements).
  A live-browser reduced-motion check ran with emulateMedia during
  acceptance and is recorded below.
- `bun run lint`: biome over the TS surface.
- `bun run typecheck`: vue-tsc over lib, tests, setup, and every Vue
  component, with a typed shim for `@slidev/client`
  (`deck/types/slidev-client.d.ts`) because the package ships .ts
  source needing Slidev's injected build globals.
- `bun run build` / `build:full`: both entries build.
- `just test` already runs the deck tests; phase 36 consolidates
  lint/typecheck into the Justfile.

### Web change (Ramon-directed, outside deck/)

The attendees panel collapses to an "Attendees (N)" pill on the
presentation page so it cannot cover the embedded deck; expanding is
an explicit override with a Hide affordance, reset on page change.
Pure rule in `web/src/calculations/attendeePanel.ts` with unit tests;
component test for the pill; e2e coverage in `room.spec.ts` for pill
visibility on all clients, expand, non-overlap with the slide
controls, hide, and the automatic full-panel return after
send-to-workspace. `just test-e2e`: 9 passed.

## Polyglot: adopted and rejected

Inspected `/home/rpg/d2/projects/polyglot` at `deck-polish-1`,
read-only. Adopted: `md magic-move` whole-frame morphs and the tagged
speaker-note convention, extended into the six-tag contract. Rejected:
self-driving `setInterval` components, mock-product dashboards, ad-hoc
per-component palettes, generic Seriph defaults with runtime Google
Fonts, 1000ms spring motion, and per-line click walks inside code
blocks (tried, then cut in review round two for click economy).

## Screenshot review

Artifacts under `artifacts/generated/deck-screens/` (gitignored,
regenerated per round): every click state of every slide at 1280x720,
final states at 1920x1080 and 1440x900, forward/backward frame pairs
proving deterministic reverse navigation, presenter mode with notes,
LiveRoom live/recovering/offline against the running backend, and the
embedded whiteboard panel with the attendee pill. Defects found by the
passes and fixed: footer stacking, dark-on-paper code tokens, diagram
label collisions, portrait-media overflow on three slides, audio-row
overflow, style-grid clipping, a truncated title, and the TUI
provenance line touching the footer.

## Deferred to phase 34 integration (named, per the prompt)

1. Banter removal in `web/src/lib/gameBanter.ts` and its test
   ("rooks before feelings", "GPU sulking" live there).
2. Tone pass over `docs/session-plan.md` and `docs/demo-plan.md`.
3. Tone pass over `web/` visible copy, errors, loading, fallbacks.
4. Widening the copy check beyond deck-owned files, if wanted.
5. Font license entry in `docs/licenses.md` (phase 34 owns the file;
   the license is recorded in `docs/deck-plan.md` meanwhile).
6. Real values for `OutcomeCompare`, the reveal table, `CostAtTarget`,
   and the A/B answers from the accepted phase 34 evidence.
7. Reconciling new phase 34 deck data or teaching components without
   reverting them, then repeating every acceptance check. The
   pre-integration results in this handover are not final acceptance.

## Known issues and tech debt

- Slidev prints a sourcemap warning for `slides/*.md` entries during
  build; harmless, upstream, not silenced.
- `deck/PLAN.md` (v1) still exists next to `PLAN_V2.md`. Left for
  history; delete only with Ramon's nod.
- Deck component tests exercise pure state functions, not mounted
  SFCs; bun cannot import `.vue` files without extra machinery. The
  browser-level behavior is covered by the screenshot passes and the
  web e2e suite.
- `typescript` is pinned to v5 in deck devDependencies. v7 breaks
  Slidev's twoslash setup at build time.
- MediaFrame detects missing assets via load error, so a corrupt file
  also shows the placeholder. Acceptable; the placeholder names the
  file either way.

## What the next stage should tackle first

Merge accepted `main` into this branch, read the phase 34 handover,
then work the deferred list above in order. After integration, rerun:
`just lint`, `just typecheck`, `just test`, `just test-e2e`, both deck
builds, the screenshot sweep at all three resolutions, and the
LiveRoom/embed checks against a running backend.

## Gotchas

- Slide separators inside imported section files are ordinary `---`;
  a stray one splits a slide. Note-contract and route tests key off
  the TIMING blocks, one per slide.
- The default route lives in `slides.md`'s src ranges. When adding or
  reordering slides in a section file, update the ranges and let
  `route.test.ts` confirm; a new optional slide needs OPTIONAL on its
  TIMING line and the test will demand a range change.
- `global-bottom.vue` layers mount before the slide body; anything
  positioned there needs a z-index above the layout's opaque ground.
- `setup/*.ts` files (shiki) are read at server start, not
  hot-reloaded. Restart the dev server after changing them.
- The stale-3030 trap from the phase 31 handover remains: a leftover
  dev server serves old code after dependency swaps.
- Playwright's `goto` to the same slide path with only `?clicks=`
  changed can hang against the dev server; drive clicks with
  ArrowRight. Long chromium sessions over all slides crash in this
  sandbox; recycle the page every few slides.
- The chess glyphs in `ChessBoard` are text; do not add an emoji rule
  covering U+2600..26FF to `copyRules.ts` or the board dies in lint.
