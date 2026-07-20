# Phase 35 handover: deck identity and copy

**Status: phase 34 integration pending. This phase is incomplete.**

Phase 35 ran in parallel with phase 34 under the two-stage workflow in
`notes/comms/p4-deck-identity-copy.md`. This branch contains the
complete deck foundation; every repository-wide obligation waits for
the accepted phase 34 result. The branch must not merge before the
integration stage below is done and all acceptance checks are repeated.

## What was built

### Design system (docs/deck-plan.md, deck/style.css)

A scoresheet-derived paper/ink system: `--paper` ground, `--ink` text,
one functional accent (`--accent`, pen blue), semantic `--good`/`--bad`
greens and reds, hairline `--rule` borders, 2px corner radii, one
component surface treatment. IBM Plex Sans and Mono self-hosted through
Fontsource packages (OFL 1.1); `fonts.provider: none` in the headmatter
so nothing fetches Google Fonts at presentation time. Fixed title,
content, and footer geometry; `global-bottom.vue` renders the footer
with a `footer: false` frontmatter opt-out for openers and full-bleed
slides. Shiki pinned to `github-light` in `deck/setup/shiki.ts`: the
default palette was unreadable on paper and vitesse-light, tried
first, is too muted for a washed-out projector.

### Slides (deck/slides.md + deck/slides/01..05)

46 slides in the exact PLAN_V2 sequence: origin (with the TUI outcome
deliberately before the chess recap), four adaptation problems with
per-modality A/B slides and a combined reveal, why-adapt, chess primer
ending in the LiveRoom handoff to the whiteboard, and a modular
technical reference. `slides.md` holds headmatter plus the title slide
and imports the five section files. Every slide carries the
TIMING/SAY/CLICK/SOURCE/CUT/FALLBACK speaker-note contract; a test
enforces the contract's presence. Measured click totals for all 46
slides are recorded in `docs/deck-plan.md`.

### Components (deck/components, deck/lib)

All educational progression is presenter-controlled. Components take a
`clicks` prop from the slide and derive their visible state through
pure functions in `deck/lib/clicks.ts`, so backward/forward navigation
restores exact frames and bun tests drive every state without a DOM.

- `DatasetShapes`: rail-and-panel stepper over the six encodings from
  `lib/datasetShapes.ts` (phase 33 values: `3980` = e2e4,
  `policy_move_reward` with FEN). Its 3.2s carousel is gone.
- `ModalityGrid`: click-revealed recipe rows; mount-timer stagger gone.
- `NotationMorph` + `ChessBoard`: one real position (Ruy Lopez after
  2...Nc6), the same move as FEN/UCI/SAN/PGN, board fixed, from/to
  squares accent-highlighted. `lib/chess.ts` parses FEN; tests caught
  an inverted square-color parity and a wrong hand-written FEN.
- `DataUniverse`: the five data circles plus the train/eval split.
- `OutcomeCompare`: matched input, BASE/ADAPTED columns, metric deltas,
  a named regression row; fixture is an explicit placeholder.
- `CostAtTarget`: the four economics rows, `[SOURCE, DATE]` cells.
- `RewardMeter`: presenter-pressed outcomes, restyled, copy tightened.
- `PhoneTuiReplay`: phone-framed local video, poster, explicit
  Play/Pause text button, placeholder describing the required recording.
- `MediaFrame`: fixed-geometry frame for every asset; missing files
  render the expected file name, content, and ratio in place.
- `LiveRoom`: phase 32 state machine and polling untouched; restyled
  with a LIVE/RECONNECTING/OFFLINE chip. All four states preserved
  (connected, connecting, recovering with stale data, unavailable).

### Checks (deck/tests, deck-local commands)

`lib/copyRules.ts` flags em dashes, emoji (the chess-glyph block
U+2600..26FF is deliberately exempt), a short stock-phrase list, and
four cliche words, with a narrow explicit allowlist (`magic-move`).
`deckCopy.test.ts` runs it over deck-owned files only, checks the
speaker-note contract, and cross-checks every referenced asset against
the placeholder inventory in `docs/deck-plan.md`. `clicks/chess/fit`
tests cover deterministic progression, reverse navigation, and
length budgets for fixed-height panels. Deck-local commands:
`bun run lint` (biome), `bun run typecheck` (tsc over lib/tests),
`bun run build`. `just test` already includes `cd deck && bun test`;
phase 36 consolidates lint/typecheck into the Justfile.

## Polyglot: adopted and rejected

Inspected `/home/rpg/d2/projects/polyglot` at `deck-polish-1`,
read-only. Adopted: `md magic-move {lines: true}` with per-frame
`{*|a-b|all}` highlight steps (two code slides), and the tagged
speaker-note convention, extended into the six-tag contract. Rejected:
every self-driving `setInterval` component (their LivePoll fabricates
votes in mock mode), the five emoji-branded mock dashboards, the
ad-hoc per-component hex palettes, generic Seriph defaults with
runtime Google Fonts, 1000ms spring motion, and absolute `v-click="N"`
indexing where relative clicks suffice.

## Screenshot review

Artifacts under `artifacts/generated/deck-screens/` (gitignored,
regenerate with a dev server plus Playwright): `walk-1280x720/` every
click state of every slide, `1920x1080/` and `1440x900/` final states,
`reverse/` forward-vs-back frame pairs for component slides,
`presenter/` presenter-mode shots, `embedded-panel*.png` the deck
inside the whiteboard Presentation page, live against the backend.

Findings, all fixed during the pass: the global-bottom footer painted
behind the slide's opaque background (needed z-index), low-contrast
Shiki tokens on paper (github-light now), two DataUniverse label
collisions (paper halo, one label moved), audio placeholder frames
tall enough to push the third row off the audio slide (audio renders
as a compact control strip now), and the style-beats slide clipping
its 2x2 bottom row (now one bounded row of four). Verified: no
overflow or
clipped code at 1280x720 across all click states, stable geometry as
clicks land, LiveRoom LIVE chip against the running backend with real
games, offline hint with the backend stopped, and the deck rendering
inside the whiteboard panel and in its own tab. The two Magic Move
slides count 12 and 18 clicks; speaker notes state the measured
numbers.

## Deliberately retained copy

Protected V2 beats, present as placeholders where the asset is
Ramon's: dog-thinking meme, "what could possibly go wrong", "Cool
bruh" with the cookie GIF, goth Minions, the corporate-lamp paragraph,
the Queen's Gambit beat, "Enough preamble, let's get started", and
"sassy as fuck" in the slide 8 SAY note (Ramon's delivery line from
PLAN_V2, speaker-facing only).

## Deferred to phase 34 integration (named, per the prompt)

1. Banter removal in `web/src/lib/gameBanter.ts` and its test
   ("rooks before feelings", "GPU sulking" live there).
2. Tone pass over `docs/session-plan.md` and `docs/demo-plan.md`
   ("moulding intelligence to your will", "five is plenty of shame",
   "rage-quitting... is a labeled data point", "more layers than a
   croissant", and similar).
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
- The component-level tests exercise pure state functions, not mounted
  SFCs; bun cannot import `.vue` files without extra machinery, and
  the repo pattern (liveRoom.ts) is logic-in-lib. If phase 36 wants
  mounted tests, it needs happy-dom plus a Vue SFC loader.
- `typescript` is pinned to v5 in deck devDependencies. v7 breaks
  Slidev's twoslash setup at build time with
  "Cannot read properties of undefined (reading 'readFile')".
- MediaFrame detects missing assets via load error, so an
  actually-corrupt file also shows the placeholder. Acceptable; the
  placeholder names the file either way.

## What the next stage should tackle first

Merge accepted `main` into this branch, read the phase 34 handover,
then work the deferred list above in order. The copy check widens only
after the phase 34 files exist in this branch. After integration,
rerun: `just lint`, `just typecheck`, `just test`, the deck build, the
screenshot sweep at all three resolutions, and the LiveRoom/embed
checks against a running backend.

## Gotchas

- Slide separators inside imported section files are ordinary `---`;
  a stray one splits a slide. The `<style>` blocks inside slides are
  fine because their content is indented CSS, never a bare `---` line.
- `global-bottom.vue` layers mount before the slide body; anything
  positioned there needs a z-index above the layout's opaque ground.
- The stale-3030 trap from the phase 31 handover remains: a leftover
  dev server serves old code after dependency swaps. One was running
  at phase start (from earlier today) and was restarted.
- Playwright's `goto` to the same slide path with only `?clicks=`
  changed can hang against the dev server; drive clicks with
  ArrowRight instead, which is also what the review script does. Long
  chromium sessions over all 46 slides crash in this sandbox; recycle
  the page every few slides.
- `setup/shiki.ts` (and any other `setup/` file) is read at server
  start, not hot-reloaded. Restart the dev server after changing it or
  the old theme keeps rendering.
- The chess glyphs in `ChessBoard` are text; do not add an emoji rule
  covering U+2600..26FF to `copyRules.ts` or the board dies in lint.
