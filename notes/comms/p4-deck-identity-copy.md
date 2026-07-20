# Phase 4 prompt: deck identity and copy

This phase may begin while phase 34 is still in progress, using the two-stage
workflow below. `deck/PLAN_V2.md` is the narrative source of truth for the
refresh. Phase 35 must not merge until the accepted phase 34 result has been
integrated and the final checks pass.

## Prompt

You are implementing phase 35 of `euro-scipy-chess-studio`: give the Slidev
deck a deliberate identity, put animation under presenter control, and remove
copy that conflicts with Ramon's direct, borderline-boring voice.

There are three distinct workshop assets and they must remain distinct:

- The tldraw whiteboard is hand-drawn, spatial, and collaborative.
- The Slidev deck is composed, paced, and designed for projection.
- The standalone Jupyter notebook is pragmatic working material and is outside
  this phase. It is not a tldraw iframe and the deck does not imitate it.

The current deck is separate from the whiteboard but still reads close to a
default dark Seriph deck with repeated slate cards. Its automatic component
timers can get ahead of the speaker. Product and deck copy also contain puns,
swagger, and familiar AI-talk phrases that do not match the requested voice.

### Parallel workflow

When phase 34 is already accepted, start from that result and complete the
whole prompt normally.

When phase 34 is still running in another workspace:

1. Start `phase-35-deck-identity-copy` from the current accepted `main`.
2. Complete the deck foundation using only `deck/`, deck-owned tests and
   assets, `docs/deck-plan.md`, and the phase 35 handover/learning guide. Do not
   inspect, copy from, or depend on the unreviewed phase 34 worktree.
3. Do not edit `api/`, `web/`, `docs/session-plan.md`, or
   `docs/demo-plan.md` during the parallel stage. Do not invent interfaces for
   phase 34 data. Use the current accepted contracts or a fixed placeholder.
4. Commit and push the foundation, but label the report `phase 34 integration
   pending`. This is a reviewable checkpoint, not a completed phase and not a
   branch that may merge.
5. After phase 34 is reviewed and merged into `main`, bring that accepted
   `main` into the phase 35 branch. Read its handover, reconcile new deck data
   and teaching components without reverting phase 34, then complete the
   repository copy pass and all acceptance checks in this prompt.

Keep the integration commit distinct from the visual-foundation commits. A
conflict is not permission to choose the phase 35 version wholesale. Inspect
the accepted phase 34 behavior and preserve it.

### Branch and boundaries

- Create `phase-35-deck-identity-copy` from the base allowed by the parallel
  workflow above.
- Read `AGENTS.md`, all of `CLAUDE.md` with particular attention to its final
  tone guide, `deck/PLAN_V2.md`, `docs/deck-plan.md`, the accepted session/demo
  plan, and every available accepted handover. Read the phase 34 handover after
  its integration if it is not available at branch creation. When an older
  narrative document conflicts with `deck/PLAN_V2.md`, the V2 plan wins for
  deck order and delivery.
- Inspect `/home/rpg/d2/projects/polyglot` on branch `deck-polish-1` as a
  reference for component variety, Shiki Magic Move, morphing, easing, and
  presenter interaction. Do not modify that repository. Do not copy its
  inconsistent colors, mock-product flourish, generic Seriph defaults, or
  other weaknesses.
- Preserve unrelated work. Do not read, edit, export, regenerate, or resolve
  anything in `notebooks/` or `web/public/notebooks/`.
- Commit coherent, tested increments throughout the phase. Push the phase
  branch, finish with no relevant untracked or uncommitted files, and do not
  merge it into `main`. Ramon reviews the summary and diff first.
- Content placeholders Ramon intends to fill are valid. If an image, video,
  audio clip, screenshot, meme, quote card, or personal asset is absent, leave
  a clearly named placeholder with its final aspect ratio and stable geometry.
  Record the expected file name/content in the source and placeholder
  inventory. Do not search for, generate, or invent substitute media. Do not
  invent final biography, resources, prices, or personal stories.
- Do not redesign the whiteboard to match the deck.
- Preserve the exact high-level sequence in `deck/PLAN_V2.md`: personal origin,
  the TUI outcome, four adaptation problems and their results, why adaptation,
  then the chess primer and technical decomposition. The TUI intentionally
  appears before the chess recap. Do not linearize that choice or drift back
  to a framework-first lecture.
- Preserve the dog-thinking meme, "what could possibly go wrong", "Cool bruh"
  and the cookie GIF, goth Minions, and the corporate-lamp paragraph. They are
  deliberate delivery beats, not stock copy for the tone pass to remove.
- Prefer the smallest deck implementation that fulfils V2. Reuse Slidev,
  existing Vue components, CSS, and native media elements. Do not add a
  dependency, component, state machine, or animation system for polish alone.
  Pragmatism beats spectacle; movement must clarify sequence, identity, or
  comparison.

### 1. Define a restrained deck system

Before editing individual slides, write a short design rationale in
`docs/deck-plan.md`. Build a system related to chess analysis, notation,
scoresheets, clocks, tournament broadcast, or editorial diagrams without
turning every slide into a chessboard.

Define and implement:

- a self-hosted, licensed type system suitable for projection and code;
- a restrained neutral palette with one functional accent and clear semantic
  colors for comparison/error/success;
- spacing, alignment, title, footer, citation, code, diagram, table, media, and
  section-transition conventions;
- stable 16:9 geometry that does not shift as content appears;
- accessible contrast and type sizes at common projector resolutions;
- a small set of component surfaces with square or modest radii, not one
  repeated floating glass card;
- a consistent way to show base versus adapted, cached versus computed, and
  one modality versus another.

Do not use decorative gradients, glowing blobs, excessive rounded cards, tiny
captions, viewport-scaled type, or generic stock imagery. Images should reveal
the actual board, artifact, model output, data, or person being discussed.

Audit the first viewport, section openings, technical code slides, comparison
slides, live room, modality grid, reward explanation, dataset shapes, closing,
and placeholder slides as a connected presentation rather than independent
templates.

The sequence must follow V2. Use section transitions and repeated visual
anchors so the later chess primer and technical decomposition clearly refer
back to results the audience has already observed.

### 2. Make components specific to their concepts

Review every existing Vue component. Keep one only if it explains something
better than native Slidev layout. Components should expose real workshop data
or a precise teaching transformation, not decorate a bullet list.

Use concept-specific treatments where useful, for example:

- dataset rows changing representation while the same move remains visible;
- reward and legality separating environment feedback from model output;
- modality comparison preserving the shared recipe while changing inputs,
  failure modes, and evaluation;
- LiveRoom showing actual room state with a useful disconnected fallback;
- base/adapted evaluation showing matched inputs and deltas;
- code transformations using Shiki Magic Move when the code itself changes.

Use Phosphor icons where icons are needed. Use visible text for commands, not
for explaining how to operate the deck. Keep each component's data and
transformation calculations separate from its Vue rendering where complexity
warrants it.

### 3. Put motion under presenter control

Replace autonomous educational timers with Slidev click progression or an
explicit presenter-controlled state. The speaker decides when the next shape,
line, result, or comparison appears.

Use motion only to preserve object identity, direct attention, compare states,
or show a transformation. Prefer restrained easing and short travel. Do not
animate every entrance. Implement `prefers-reduced-motion` behavior and ensure
the final state remains understandable without animation.

Clear component timers and subscriptions on unmount. Navigating backward and
forward must restore deterministic component state. Click count and speaker
notes must agree.

### 4. Run a complete tone pass

Remove the banter system or reduce it to factual chess event messages. Delete
phrases such as "rooks before feelings", "GPU sulking", "Pawns dream", "not
vibes", "pocket money", "all yours to keep", and similar attempts at wit.
Do not replace them with different jokes.

During the parallel foundation, audit deck copy and speaker notes only. After
the accepted phase 34 result is integrated, audit all visible app copy,
session/demo documents, errors, loading states, and fallback messages too.
Apply these rules:

- direct, terse, practical;
- no emojis or em dashes;
- no hype, sentimentality, marketing claims, or emotional closing language;
- no AI cliches such as magic, democratize, game-changing, journey, unlock,
  supercharge, or future-is-here language;
- no swagger about price, hardware, hallucination, or model superiority;
- prefer concrete nouns, measured values, and clear verbs;
- keep Ramon's deliberate personal story and every explicitly protected V2
  delivery beat, without adding surrounding banter.

Add a lightweight, maintainable copy check for banned punctuation and a short
list of genuinely unwanted stock phrases. It should support a narrow explicit
allowlist and should not pretend tone can be completely linted.

Do not add that check to phase 34-owned files during the parallel foundation.
Wire it into the accepted repository only during the integration stage.

### Tests and visual acceptance

Add component tests for deterministic progression, reverse navigation,
reduced motion, live/offline data states, and long-content fit. Add the deck to
the normal lint/typecheck/build surface if phase 36 has not yet done so, or
leave a documented minimal command that phase 36 can consolidate.

Build the Slidev deck and inspect screenshots at least at:

- 1920x1080 projector;
- 1440x900 laptop;
- 1280x720 constrained projector;
- presenter mode with speaker notes where practical.

Check every slide for overflow, clipped code, overlapping click layers,
unreadable captions, missing assets, layout shifts, and placeholders that no
longer have enough room. Verify LiveRoom against a running backend. Test the
deck from the embedded whiteboard panel and in its own tab. Do not add or test
a notebook iframe; Jupyter is opened separately when the accepted run of show
calls for it.

Run `just lint`, `just typecheck`, `just test`, the deck build, and relevant
E2E checks. Record screenshot paths or a visual-regression artifact in the
handover. Do not report visual completion from a successful build alone.
When running in parallel, repeat these checks after integrating phase 34. The
pre-integration result is not sufficient for final acceptance.

### Documentation and final report

Update `docs/deck-plan.md` with the design system, component inventory, motion
rules, placeholder inventory, asset sources, and slide-by-slide click-count
expectations where useful. Update session/demo copy affected by the tone pass.

Create:

- `notes/ai/phase-35-deck-identity-copy.md`
- `notes/hu/phase-35-deck-identity-copy.md`

The handover must distinguish what was inspired by Polyglot, what was rejected,
which placeholders remain for Ramon, what copy was deliberately retained, and
what the screenshot review found. If phase 34 is still pending, it must also
name every deferred integration and say plainly that phase 35 is incomplete.
The learning guide should ask why a shared design system does not require every
component to look identical and why an automatic three-second transition is a
teaching decision, not merely an animation setting.

Finish with a concise summary of the visual system, motion model, copy changes,
checks run, and remaining Ramon-owned placeholders.
