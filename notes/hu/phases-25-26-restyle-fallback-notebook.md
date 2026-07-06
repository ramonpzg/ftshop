# Learning guide: phases 25-26, taking the color out and putting the session in a file

Two phases, one theme: reducing surface area. Phase 25 removed
everything from the UI that wasn't information. Phase 26 compressed the
entire workshop into a single Python file that runs with nothing but uv
and a laptop. Both are exercises in asking what you can delete before
asking what you can add.

## Why the colors had to go

You spotted it yourself: colored cards with accent borders are the
visual equivalent of "as an AI language model." Every scaffolded app
looks like that because every training set is full of dashboards that
look like that. The fix was not a tasteful new palette. It was grayscale
plus tldraw's own hand-drawn font, so the panels look like they belong
on the whiteboard instead of hovering above it in a different universe.

Here is the question worth sitting with: why did the font change do
more work than the color change? Look at a panel before and after.
`tldraw_draw` is loaded globally by tldraw.css for the canvas shapes,
so borrowing it costs nothing and buys coherence. The UI stops
announcing "I am chrome" and starts reading as part of the drawing.
Squint at the app and try to find the boundary between a seeded frame
and the workspace panel. That boundary is now a texture change, not a
color change, and texture is what the eye actually trusts.

## The tooltip bug, or: the browser was doing exactly what we said

The phase 19 tooltips were native `title` attributes, and they never
showed. Not flaky. Never. Before reading on: the tooltips worked
perfectly in edit mode. What is different about a tldraw shape outside
edit mode?

The answer is one CSS property. tldraw sets `pointer-events: none` on
shape containers you have not double-clicked into, so the canvas
receives every event for select and drag. No pointer events means no
hover, no hover means no `title`. The fix is surgical: the section
`h3`s opt back in with `pointer-events: auto`. Events still bubble up
through the container, so dragging the panel by its header still works.
One line, but you have to know the line exists in two stylesheets,
WorkspacePanel.css and ModalityPanel.css, and the phase 25 playwright
script now checks that an h3 receives the pointer while not editing,
because a bug that invisible will absolutely come back.

Ask yourself what the general lesson is. The bug was not in our code.
Every layer behaved as documented. The failure lived in the composition
of two correct systems, which is where the interesting bugs always
live, and why "it works in edit mode" was the whole diagnosis if we had
listened to it sooner.

## Sections that collapse, and why the grid died

The old layout was a CSS grid with named template areas. Elegant in the
stylesheet, hostile in the room: the grid decided how tall the board
section was, the board section decided the Start button was below the
fold, and there was no scrollbar because the section didn't know it was
clipped. You literally could not start a game.

The replacement is three flex columns of collapsible sections. Every
section body gets the flexbox incantation `flex: 1; min-height: 0;
overflow-y: auto`. Why `min-height: 0`? Because flex items default to
`min-height: auto`, meaning "never smaller than my content," which
quietly forbids the overflow you just asked for. This is the single
most-Googled line of CSS in existence and it earns its reputation.

Collapse state persists per section in localStorage under
`euro-chess-studio:section-open:<id>`. Notice what does not persist:
order. You cannot drag sections around. That was a judgment call worth
interrogating. The complaint was "I cannot reach the Start button," and
collapse-plus-scroll kills that dead. Drag-to-rearrange means persisted
per-user layout, a new table or a fatter localStorage schema, and drag
interactions inside a canvas that already owns dragging. What would you
have done with ninety minutes: build that, or build the fallback
notebook? Phase 26 is the answer we chose.

## The notebook: same recipe, no whiteboard

`notebooks/full-session.py` exists because of a question every live
demo must answer: what happens when it dies on stage? The app's answer
used to be "reset the database and pray." Now it is
`just session-notebook`, which opens the entire session as one marimo
notebook. Not a summary of the session. The session: the scripted game,
the reward function, all six dataset shapes, the templates, the gated
model opponent, the evals, the training ladder, image, audio, video,
merging, closing argument. Someone who grabs the file without ever
seeing the app misses the shared canvas and nothing else.

The trick that makes it standalone is PEP 723, the inline script
metadata block at the top of the file. The dependencies live in a
comment, `uvx marimo edit --sandbox` reads them, builds a throwaway
venv, and runs. No `pip install`, no environment.yml archaeology, no
"works on my machine." The notebook is its own lockfile-shaped
manifest. This is also why the notebook duplicates `compute_reward`
and the dataset builders instead of importing them from the api
package: an import would chain the notebook to the repo's venv and the
whole standalone promise collapses. We chose duplication and wrote the
drift risk down in the handover, which is the adult way to duplicate
code.

Worth pausing on: why does the notebook run at all with zero API keys?
One cell builds a `CAPS` dict up front, probing for OPENAI_API_KEY,
FAL_KEY, torch, flax, and modal. Every expensive cell checks its
capability and renders a how-to-enable hint instead of a stack trace.
The gating pattern is the same one the app uses for its disabled
buttons, which is not a coincidence, it is the same lesson: degrade to
an explanation, never to an error.

And the bridge back to the app is one `Path` check. If
`data/processed/text/chess_sft.jsonl` exists, the file the app's
Export dataset button writes, the notebook trains on the room's actual
games. If not, it writes its own copy from the scripted game to /tmp.
Play on the whiteboard, train in the notebook, and if the whiteboard
never existed, nobody in the notebook can tell.

## The part where a transformer trains inside a cell

The training ladder's top rung is not a code sample, it runs. A
character-tokenized TinyLM in flax.nnx trains 150 steps on CPU in a few
seconds and plots its loss falling from 3.25 to 0.44. Why bother, when
no one will ever play chess against a model that small? Because every
other rung of the ladder, Unsloth, axolotl, Modal, needs a GPU someone
may not have, and a loss curve you watched fall in real time is worth
more than three slides about loss curves. It is the Karpathy microchat
argument in miniature: the recipe fits in your head when the model
fits in your RAM.

One flax detail that will bite anyone copying older tutorials: the nnx
optimizer now wants `nnx.Optimizer(model, optax.adamw(...),
wrt=nnx.Param)` and `optimizer.update(model, grads)` with the model as
the first argument. The internet's snippets predate this. Ours does
not.

## How we know the notebook works

You cannot unit test a notebook in the usual sense, but marimo files
are just Python: `uv run notebooks/full-session.py` executes
`app.run()`, which runs every cell in dependency order and raises on
the first error. Exit code zero with no keys set proves all the gates
close cleanly. A probe script then called `app.run()` directly and
inspected the 49 returned defs: 9 game records, 54 dataset rows across
six shapes, a trained model, a falling loss list. That probe took ten
minutes to write and is the difference between "the file parses" and
"the session runs." When you edit the notebook, rerun it. Both
commands are in the handover.

One marimo rule to internalize before you edit: cell-level variable
names are globally unique across the whole notebook, except names
starting with an underscore, which are cell-local. The notebook uses
`_r`, `_source`, `_legal_rate` everywhere precisely so cells stay
self-contained. If marimo greets your new cell with a redefinition
error, you have just learned this rule the traditional way.
