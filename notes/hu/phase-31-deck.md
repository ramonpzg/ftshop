# Learning guide: phase 31, three assets and the discipline of a plan

The workshop now has three legs: the board where the room works, the
deck where the story lives, the notebook that survives everything.
This phase built the second leg and taught a few things about how
presentations are software.

## Why plan a deck like a codebase

The polyglot workflow you used at PyCon AU got reused wholesale:
before any slide exists, docs/deck-plan.md says what each one
contains, how it moves, which images it needs (with the exact
generation prompt), and which components it depends on. Then you
build in bouts of five.

Ask why this beats opening slides.md and typing. A deck has the same
failure mode as a codebase grown without design: locally fine slides
that do not add up to an argument. The plan is where the argument
lives; the slides are its implementation. It also makes the deck
reviewable before it is watchable, which is the same reason code
review reads diffs and not running programs. And the image prompts
in the plan mean the art direction survives even though the images
do not exist yet. Placeholders in the deck carry their own prompts:
the slide presents cleanly today and documents its missing asset at
the same time.

## Animations are claims

The rule carried over from polyglot: every motion makes a point.
Three magic-moves do the heaviest teaching in the deck, and each one
is an argument stated as a transformation. The cost table morphs
from train-from-scratch to fine-tune: same five rows, every number
shrinks except what you get. The prompt template morphs into the
chat template into the rendered turn: most fine-tuning bugs live
between those steps, and now the audience has watched the text
travel through them. The training ladder morphs Unsloth code into
axolotl YAML into a JAX loss: same run, different costume, which is
the entire point of the ladder.

Compare that to a bullet list saying "there are five abstraction
levels". The information is identical. The understanding is not,
because the morph shows what stays constant while the surface
changes, and "what stays constant" is precisely the lesson.

## Components with one accent

Four Vue components, in the glassy style you liked from polyglot,
with one deliberate improvement: a single amber accent instead of a
color per concept. Polyglot's components each had their own palette;
twelve slides in, color stopped meaning anything. Here amber always
means "the live number worth watching": samples in the room, the
active clock, the reward that just landed. A design system with one
rule you never break beats one with five rules you sometimes follow.

The one component that earns its complexity is LiveRoom: it polls
the same /presenter/games endpoint the dashboard uses and puts the
room on a slide. Everyone sees their own game on the projector. Note
what it does when the backend is down: one terse sentence saying how
to fix it. Components that go in front of an audience need offline
states the way trapeze artists need nets, and for the same reason.

## The hall of mirrors, declined

The board now embeds the deck in an iframe on the Presentation page.
The deck could also embed the board (slide 9 wants a screenshot of
it). Nothing technically prevents the board embedding the deck
embedding the board, at which point you present a recursion instead
of a workshop. The panel exists so the three assets share one
surface when that is convenient; the Open link exists because the
deck's own tab is where presenter mode and speaker notes live.
Embedding is a convenience, not an architecture. Know which one you
are building.

One small trap worth remembering: the deck iframe is cross-origin,
so the board cannot ask "is the deck server up" the way the notebook
panel probes its same-origin WASM build. The fix is not clever
engineering; it is a header that says "Blank? Run: just deck". Some
problems are documentation wearing a bug costume.

## The notebook, now also prose

`just notebook-md` exports the marimo notebook to markdown, checked
in next to the source. Same content, third form: runnable Python,
and now readable prose with fenced code. Why bother? Because the
person who finds the repo six months from now will read before they
run, and a .py file full of app.cell decorators reads like a machine
wrote it for a machine. The markdown is the notebook holding the
door open. It is generated, so editing it by hand is a trap the
header comment warns about: fix the notebook, regenerate the prose.
