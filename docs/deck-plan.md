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
presentation time, no Google Fonts. All three families are licensed
under the SIL Open Font License 1.1; license files ship inside the
packages under `deck/node_modules/@fontsource/*`. `docs/licenses.md` records
the IBM Plex and Shantell Sans attributions.

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

## Two styles, one deck

Every slide, layout, click count, and motion rule is shared between
two launch-time styles; only tokens and typefaces change, and a test
(`tests/theme.test.ts`) asserts the chalk block overrides every color
token paper defines.

- **paper** (default): the light scoresheet system below.
  `just deck`, `bun run dev`, `bun run build`.
- **chalk**: near-black ground, light ink, slightly hand-written
  Shantell Sans (the family tldraw uses for its draw style, OFL 1.1
  via Fontsource), rounder 6px surfaces, dark Shiki palette. It sits
  next to the tldraw whiteboard without importing its hand-drawn
  shapes. `just deck chalk`, `bun run dev:chalk`,
  `bun run build:chalk`. Combine with the full route manually:
  `VITE_DECK_STYLE=chalk bun run dev:full`.

The switch is `VITE_DECK_STYLE`, read once at server or build start in
`deck/setup/main.ts`; chalk's fonts load only when selected.

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
| `OutcomeCompare` | matched input, base/adapted outputs, metrics with deltas, one regression | accepted phase 34 scripted replay, labelled as authored evidence |
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

Assets Ramon supplies. Every one renders through `MediaFrame` or
`PhoneTuiReplay` with the stated file name and aspect ratio; the slide
is complete the moment the file lands in `deck/public/assets/`. A deck
test asserts every referenced file name appears in this table.

| file | ratio | content |
| --- | --- | --- |
| `cover.jpg` | 4:3 | one strong chess image or a frame of the actual TUI board |
| `origin-photo.jpg` | 4:3 | childhood photo, readable from the back |
| `old-book.jpg` | 3:4 | the chess book, photographed as an object |
| `duolingo-launch.png` | 16:9 | Duolingo chess launch post screenshot |
| `duo-example-cmate.jpg` | 9:19.5 | Duolingo chess app screenshot |
| `oscar-game.png` | 9:19.5 | one game against Oscar, app screenshot |
| `oscar.png` | 9:19.5 | Oscar |
| `queens-gambit.jpg` | 16:9 | Queen's Gambit still |
| `no-internet.jpg` | 9:19.5 | Duolingo chess offline on the Sydney flight |
| `frustrated.jpg` | 1:1 | frustration reaction, no-internet overlay |
| `plane-chair-meme.png` | 4:3 | plane-seat meme, no-internet overlay |
| `burning-house.jpg` | 4:3 | burning-house meme, reasonable-response overlay |
| `meme-dog-thinking.jpg` | 1:1 | the dog-thinking meme |
| `tui-recording.mp4`, `tui-poster.png` | 9:19.5 | Termux TUI session per PLAN_V2 slide 8 |
| `mapping-game.png` | 4:5 | the completed board and game log the mapping slides share |
| `image-base.png`, `image-adapted.png` | 1:1 | image adaptation pair, same prompt |
| `image-style-2.png` | 1:1 | optional second style |
| `audio-capture.wav` | audio | a capture: wooden piece on wood |
| `audio-genre.wav` | audio | background music, one genre |
| `audio-move.wav` | audio | optional spoken move |
| `video-scene.mp4`, `video-scene-poster.png` | 16:9 | Luna scene video, no chess objects |
| `chess-log.png` | 9:16 | completed board and game log for the mapping slides |
| `sun-tzu.jpg` | 1:1 | Art of War quote image for the TUI objective |
| `gemma-webui-1.jpg`, `gemma-webui-2.jpg` | 9:19.5 | llama.cpp web UI in a phone browser |
| `duo-chess-sound.mp4` | 9:19.5 | Duolingo chess screen recording with sound |
| `ab-text-a.png`, `ab-text-b.png` | 16:10 | text A/B pair, rendered replies |
| `ab-image-a.png`, `ab-image-b.png` | 1:1 | image A/B pair |
| `ab-audio-a.wav`, `ab-audio-b.wav` | audio | audio A/B pair |
| `ab-video-a.mp4`, `ab-video-b.mp4` | 16:9 | video A/B pair |
| `goth-minions.jpg` | 4:3 | goth Minions |
| `corporate-lamp.txt` | text block | the jargon-heavy lamp announcement paragraph |
| `style-translation.mp4` | 16:9 | bachata background or Thinking Machines translation clip |
| `canva-template.mp4` | 16:9 | the real Canva video-template example |
| `meme-cookie.gif` | 1:1 | chunky boy deciding which cookie to eat |
| `future-tree.png` | 16:9 | the model tree diagram from v1 |

Text placeholders pending from Ramon, marked PLACEHOLDER in the slide
source: the three real-world mappings and their approved edits, the
Luna scene prompt, the four A/B answers with provenance, the
reveal-table rows, all economics numbers, the recorded TUI result,
and the repo URL/QR on the closing slide. Phase 34's image, audio, and
video media are in-repo illustrations, not adapted-model outputs, so
they do not fill the A/B questions. The text comparison uses phase
34's scripted replay and states on screen that no model was trained.

## Deck commands

Deck-owned until phase 36 consolidates them into the Justfile:

```
cd deck && bun run dev        # default route on :3030
cd deck && bun run dev:full   # full route incl. optional slides
cd deck && bun run build      # default-route build to dist/
cd deck && bun run build:full # full-route build
cd deck && bun test           # lib + copy + route checks (in `just test`)
cd deck && bun run lint       # biome, deck only
cd deck && bun run typecheck  # vue-tsc over lib, tests, components
```

`just test` already runs the deck tests. Lint and typecheck are not yet
in the root Justfile; phase 36 wires them in.

## Default route and timing

PLAN_V2 budgets 20 to 25 minutes for the opening deck (parts 1-4, up
to the point the room moves to the whiteboard). `deck/slides.md` is
the single default deck, all five parts, 43 slides after its `src`
ranges exclude exactly the OPTIONAL slides named in the speaker
notes; `tests/route.test.ts` asserts those ranges stay exact. It is
**not** itself a 20-25 minute file: parts 1-4 hit that budget, and
part 5 (technical reference) continues in the same file for a
presenter who wants to keep going rather than move to the whiteboard
immediately. `deck/slides-full.md` imports every slide, optional ones
included, for rehearsal (`bun run dev:full`).

| part | default | slides skipped by default |
| --- | --- | --- |
| 1 origin | 5:35 | Oscar (0:30) |
| 2 outcomes | 9:15 | mappings two and three (1:30) |
| 3 why adapt | 6:20 | the model tree (0:45) |
| 4 chess primer | 4:55 | none |
| **opening (1-4)** | **26:05** | optional adds up to 2:45 |
| 5 technical reference | 14:55 | modular, see below |
| **slides.md total** | **41:00** | |

The opening runs 1:05 over the 20-25 minute budget since the browser
bridge and the Duolingo sound clip joined part 2; rehearsal decides
what shaves back, starting from the cut order below.

The room-join dead air (up to 90 seconds) is budgeted in the LiveRoom
slide's note on top of its talking time. The last slide of part 4
("The room, live") is the deck's hard stop for the default 90-minute
run of show: its CUT note names it as the handoff to the
whiteboard, and PLAN_V2 treats part 5 as optional continuation
covered on the whiteboard or in the notebook instead. If time runs
short mid-deck, the cut order is: the optional slides above, then the
A/B clip playback, then all of part 5.

## Click-count expectations

Each slide's `CLICK:` speaker-note line states what changes and why.
The totals below were measured against the running deck during the
phase 35 screenshot pass (slide number: clicks).

```
1:0   2:1   3:1   4:1   5:4   6:0   7:3   8:1
9:4   10:1  11:1  12:1  13:1  14:1  15:3  16:0  17:3  18:2
19:0  20:0  21:0  22:0  23:4
24:0  25:3  26:1  27:4  28:5  29:0  30:0  31:0  32:0  33:0
34:0  35:3  36:3  37:2  38:0
39:0  40:5  41:5  42:0  43:2  44:2  45:2  46:0  47:0  48:2  49:1
```

49 slides, numbered on the full route; the default route drops slides
4, 12, 13, and 31. Slide 14 is the browser bridge, 16 the Duolingo
sound clip. The A/B slides (17 to 20) have zero clicker clicks:
their answers are `<details>` disclosures outside the Slidev click
sequence, opened with a direct click or Enter on the focused summary,
held for the combined reveal by default.
The two Magic Move code slides morph whole frames with no inner
line-highlight steps, so they cost two clicks each; the ladder summary
is its own zero-click slide.
