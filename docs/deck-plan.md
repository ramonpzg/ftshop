# Deck plan

The Slidev deck is one of the workshop's three assets: the board is
where the room works, the deck is where the narrative lives, the
standalone Jupyter notebook is pragmatic working material and the
take-home. The three keep separate visual languages: hand-drawn
whiteboard, composed deck, plain notebook.

`deck/PLAN_V2.md` is the narrative source of truth for slide order and
delivery. This document records the deck's design system, component
inventory, motion rules, placeholder inventory, and per-slide click
expectations. The v1 slide list that used to live here is superseded by
PLAN_V2.

## Design rationale

The deck borrows its look from the printed side of chess: scoresheets,
annotated game columns, tournament wallboards. Those objects are almost
entirely black ink on paper, set in a small number of type sizes, ruled
into columns, with one pen color for marks that matter. That maps
cleanly onto what this deck must do: show notation, code, evidence
tables, and before/after comparisons, and stay readable from the back
of a bright room.

Concretely that means a paper-white ground, near-black ink, thin rules
instead of boxes where possible, square corners, tabular figures for
anything counted or timed, and one functional accent used the way an
arbiter uses a pen: to mark the thing being decided. It is not a
chessboard theme. No slide is dressed as a board; the board appears
only when an actual position is being discussed.

Every slide is one visual beat. Density lives in the speaker notes, not
on the canvas.

## Type system

Self-hosted through Fontsource npm packages: no network fetch at
presentation time, no Google Fonts. Both families are licensed under
the SIL Open Font License 1.1; license files ship inside the packages
under `deck/node_modules/@fontsource/*`. `docs/licenses.md` gets the
entry at phase 34 integration, since phase 34 owns that file right now.

- `IBM Plex Sans` for display and body. Weights 400, 500, 600, 700.
- `IBM Plex Mono` for code, notation, clocks, metrics, citations.
  Weights 400, 500, 600.

Scale, on Slidev's 980x552 canvas (scaled to the projector):

| role | size | weight | face |
| --- | --- | --- | --- |
| display (section titles, big statements) | 3.4rem | 700 | Sans |
| slide title | 1.9rem | 700 | Sans |
| body | 1.05rem | 400 | Sans |
| table/metric | 0.9rem | 400-600 | Mono |
| code | 0.85rem | 400 | Mono |
| kicker, footer, citation | 0.7rem | 500 | Mono, uppercase, letterspaced |

Nothing on a content slide goes below 0.7rem, and 0.7rem is reserved
for the footer and citation rows. No viewport-scaled type.

## Palette

Neutral ground, one functional accent, two semantic colors. All values
are CSS custom properties in `deck/style.css`; components use the
variables, never raw hex.

| token | value | use |
| --- | --- | --- |
| `--paper` | `#f6f4ef` | slide ground |
| `--paper-raised` | `#fdfcf9` | component surfaces, code blocks |
| `--ink` | `#191713` | text, titles, board diagrams |
| `--ink-soft` | `#5c564c` | secondary text, speaker asides |
| `--ink-faint` | `#8a8377` | kickers, footers, disabled |
| `--rule` | `#d9d3c7` | hairlines, table rules, borders |
| `--accent` | `#1f4fd8` | the arbiter's pen: current move, adapted result, live data, active state |
| `--good` | `#1e6b45` | improvement, success, legal |
| `--bad` | `#a2352a` | regression, error, illegal |

Contrast: ink on paper is about 14:1, accent on paper 6.8:1, good
6.3:1, bad 6.4:1. All pass at body sizes on a washed-out projector.
Dark slides exist only as full-bleed media frames (the TUI recording,
video clips); their captions sit on the media, in paper white.

## Conventions

- **Alignment.** Left-aligned text on a 12-column mental grid. Centered
  content only on section openers and single-object slides.
- **Titles.** A mono uppercase kicker names the part (for example
  `PART 2 · FOUR ADAPTATION PROBLEMS`), the sans title states the
  point. Kicker and title sit at a fixed top position on every content
  slide.
- **Footer.** Every content slide: hairline rule, then
  `SAME RECIPE, DIFFERENT RESULTS · EUROSCIPY 2026` left, slide number
  right, in mono at 0.7rem. Section openers and full-bleed media
  slides omit it.
- **Citations and provenance.** One mono line under the object:
  model or adapter id, exact input reference, `CACHED <date>` or
  `LIVE`, source. Prices and external claims carry `[SOURCE, DATE]`
  placeholders until checked.
- **Code.** Shiki with a light theme on `--paper-raised`, hairline
  border, square corners. Magic Move only when the code itself is the
  thing changing. Line highlighting steps under presenter clicks.
- **Diagrams.** Ink lines on paper, editorial style. No mermaid brand
  colors, no drop shadows.
- **Tables.** Hairline horizontal rules only, mono figures, first
  column sans. Reveal by row when the comparison is the point.
- **Media.** Images and video sit in fixed-geometry frames with a
  caption row reserved whether or not the caption is visible.
  Placeholders occupy the same frame as the final asset.
- **Section transitions.** Each of the five parts opens with a
  scoresheet-style opener: oversized part number, part title, hairline
  rules, no footer. Slide transition stays on a quick fade;
  within-slide motion carries meaning instead.

## Geometry

16:9 throughout, Slidev's 980x552 canvas. Rules:

- Title block, content region, and footer have fixed positions.
  Clicks toggle visibility inside reserved space; they never insert
  layout that moves neighbors.
- Media frames declare aspect ratio in CSS (`aspect-ratio`), so a
  missing asset and its eventual file occupy identical space.
- Comparison layouts (base/adapted) reserve both columns from click
  zero.
- Long lists never scroll on stage; content that does not fit at
  1280x720 gets split across slides instead.

## Component surfaces

One surface treatment: `--paper-raised` ground, 1px `--rule` border,
2px corner radius, no shadow, no blur, no gradient. Interactive
affordances (RewardMeter buttons) get an ink border on hover and an
accent border when active. No floating glass cards.

## Comparison conventions

- **Base versus adapted.** Two columns, mono labels `BASE` and
  `ADAPTED`; the adapted column carries a 2px accent top border.
  Deltas print signed values: green for improvement, red for
  regression, on the metric they refer to.
- **Cached versus live.** A mono chip after the citation: `CACHED
  2026-06-30` outlined in `--rule`, or `LIVE` outlined in `--accent`
  with a solid accent dot. Components that poll the backend show the
  same chip.
- **Modality versus modality.** The recipe grid keeps one fixed row
  order (text, image, audio, video) and one fixed column order (pairs
  in, adapter out, eval always) everywhere it appears. A modality is
  named in sans; its data is set in mono.

## Motion rules

- Every educational transition is presenter-controlled: Slidev clicks
  or an explicit control the presenter operates. No `setInterval`
  carousels, no staggered reveals on mount, no autoplay.
- Motion preserves object identity (the same board while labels
  change), directs attention (one element enters), or shows a
  transformation (Magic Move). Entrances that do none of these do not
  animate.
- Easing `cubic-bezier(0.25, 0.1, 0.25, 1)`, durations 150-400ms,
  travel under 24px. No springs, no rotation, no scale-from-zero.
- `prefers-reduced-motion: reduce` collapses all transition and
  animation durations to 1ms globally (in `style.css`); every final
  state reads correctly as a static frame.
- Components derive their visible state purely from the click count
  they are handed, so backward and forward navigation always lands on
  the same frame. Timers and subscriptions are cleared on unmount
  (LiveRoom's poll loop is data fetching, not motion, and keeps its
  interval while mounted).

## Component inventory

All components take a `clicks` prop where they participate in slide
progression; the mapping from click count to visible state lives in
pure functions under `deck/lib/` so tests can drive it without a DOM.

| component | concept | data |
| --- | --- | --- |
| `PhoneTuiReplay` | the TUI outcome as a phone-shaped local video with poster and explicit play control | local file, placeholder until recorded |
| `OutcomeCompare` | matched input, base/adapted outputs, metrics with deltas, one regression | fixed placeholder fixtures until phase 34 integration |
| `DatasetShapes` | one move re-encoded, click-stepped | static, real encodings |
| `RewardMeter` | environment feedback separated from model output; presenter presses outcomes | static reward map |
| `CostAtTarget` | one task at a target quality, measured deployment facts | `[SOURCE, DATE]` placeholders |
| `DataUniverse` | the data circles narrowing, then the train/eval split | static |
| `NotationMorph` | one position and one move across FEN, UCI, SAN, PGN with the board fixed | real game data |
| `LiveRoom` | actual room state via `GET /presenter/games`, offline fallback | live backend |
| `MediaFrame` | fixed-geometry placeholder and final-media frame with caption and provenance rows | per-slide |

Removed: `ModalityGrid`'s mount-timer stagger (the recipe grid is now
click-revealed), `DatasetShapes`' 3.2s carousel.

## Placeholder inventory

Assets Ramon supplies. Every one renders through `MediaFrame` with the
stated file name and aspect ratio; the slide is complete the moment the
file lands in `deck/assets/`.

| file | ratio | content |
| --- | --- | --- |
| `assets/origin-photo.jpg` | 4:3 | childhood photo, readable from the back |
| `assets/origin-book.jpg` | 3:4 | the chess book bought and abandoned |
| `assets/duolingo-launch.png` | 16:9 | Duolingo chess launch post screenshot |
| `assets/duolingo-app.png` | 9:19.5 | Duolingo chess app screenshot |
| `assets/oscar-game.png` | 9:19.5 | one game against Oscar, app screenshot |
| `assets/oscar.png` | 9:19.5 | Oscar himself |
| `assets/queens-gambit.jpg` | 16:9 | Queen's Gambit still |
| `assets/no-internet.png` | 9:19.5 | Duolingo chess offline on the Sydney flight |
| `assets/meme-dog-thinking.jpg` | 1:1 | the dog-thinking meme |
| `assets/tui-recording.mp4` + `assets/tui-poster.png` | 9:19.5 | Termux TUI session per PLAN_V2 slide 8 |
| `assets/meme-cookie.gif` | 1:1 | chunky boy deciding which cookie to eat |
| `assets/goth-minions.jpg` | 4:3 | goth Minions |
| `assets/corporate-lamp.txt` | text block | the jargon-heavy lamp announcement paragraph |
| `assets/style-translation.mp4` | 16:9 | bachata background or Thinking Machines translation clip |
| `assets/canva-template.mp4` | 16:9 | the real Canva video-template example |
| `assets/mapping-{1,2,3}.png` | 16:9 | three real-world mapping artifacts (board, log, mapping) |
| `assets/image-{base,adapted}.png` | 1:1 | image adaptation pair, same prompt |
| `assets/audio-{base,adapted}.wav` | native audio | audio adaptation pair |
| `assets/video-scene.mp4` + poster | 16:9 | Luna scene video, no chess objects |
| `assets/ab-{text,image,audio,video}-{a,b}.*` | per modality | the four A/B pairs with provenance |
| `assets/future-tree.png` | 16:9 | the model tree diagram from v1 |

## Deck commands

Deck-owned until phase 36 consolidates them into the Justfile:

```
cd deck && bun run dev        # slidev on :3030
cd deck && bun run build      # production build to dist/
cd deck && bun test           # lib + copy checks (already in `just test`)
cd deck && bun run lint       # biome, deck only
cd deck && bun run typecheck  # tsc over lib/ and tests/
```

`just test` already runs the deck tests. Lint and typecheck are not yet
in the root Justfile; phase 36 wires them in.

## Click-count expectations

Recorded per slide in the speaker notes (`CLICK:` lines) inside
`deck/slides/*.md`. The copy test asserts the notes contract exists;
the click counts themselves are verified against the built deck during
the screenshot pass.
