# Handover: phases 25-26, monochrome restyle and the fallback notebook

Written 2026-07-06, third batch of the review branch. Read the two
earlier handovers first; this builds on both.

## What was built

**Monochrome restyle (25).** All accent colors are gone. The workspace
panel, modality panels, notebook panels, page tabs, join form, and
presenter chrome are black, white, and grays, set in `tldraw_draw` (the
hand-drawn face tldraw.css loads globally; `tldraw_mono` for pre/code).
Ramon flagged the colored-card look as a recognizable AI-generated
pattern; the fix was deletion, not a new palette.

**Page tabs (25).** `.page-tabs` is nowrap + `overflow-x: auto` with
`flex: 0 0 auto` tabs, so titles keep their natural width and a narrow
window scrolls instead of squeezing.

**Tooltips actually work now (25).** tldraw shape containers are
`pointer-events: none` outside edit mode, which silently swallowed
every hover, so the native `title` tooltips from phase 19 never fired
unless you had double-clicked in. Section `h3`s now set
`pointer-events: auto`; events still bubble, so canvas select and drag
are unaffected. A playwright check confirms the h3 receives the pointer
while not editing.

**Workspace layout rebuilt (25).** The rigid named-area grid clipped
content: Ramon could not reach Start game or scroll the board section.
Now three flex columns (board/config/eval, dataset/analysis/artifact,
mini IDE) of collapsible `Section`s. Each section header carries a
toggle (edit mode only, `data-testid="section-toggle-<id>"`); open
state persists per section in localStorage
(`euro-chess-studio:section-open:<id>`). Bodies get `flex: 1;
min-height: 0; overflow-y: auto`, so every section scrolls
independently. An open board section flexes larger
(`[data-section="board"][data-open="true"] { flex: 1.8 }`).

**The fallback notebook (26).** `notebooks/full-session.py` is the
entire session as one standalone marimo notebook, ~920 lines, mapping
one to one to the whiteboard pages: scripted Ruy Lopez producing
`game_records`, `compute_reward`, all six dataset shapes into
`all_rows`, prompt + Jinja2 chat templates, a gated LLM opponent
(same lesson: illegal model moves score -1 and do not advance the
board), real-world mapping, JSONL export, computed evals, the training
ladder (Unsloth code for `unsloth/gemma-4-E2B-it`, axolotl YAML with
`chat_template: gemma4`, and a live JAX TinyLM that trains 150 steps
on CPU with a loss plot), a Modal sandbox sketch, fal image generation
+ VLM-as-judge (gated), local audio (a numpy click synth + spectrogram
that always runs, musicgen gated), fal video (gated), mergekit, and
the closing argument.

Dependencies ride in PEP 723 inline metadata, so
`uvx marimo edit --sandbox notebooks/full-session.py` (now
`just session-notebook`) resolves marimo, numpy, matplotlib,
python-chess, httpx, jinja2, flax, and optax without touching the api
venv. A `CAPS` dict probes OPENAI_API_KEY, FAL_KEY, torch, flax, and
modal once; every gated cell renders a how-to-enable hint instead of
erroring. The dataset cell prefers the app's exported
`data/processed/text/chess_sft.jsonl` (cwd-relative; run from repo
root) and falls back to writing its own copy under $TMPDIR.

Validated headless: `uv run notebooks/full-session.py` exits 0 with no
keys set, and an `app.run()` probe confirms all 49 defs materialize,
54 rows across the six shapes from 9 plies, and the JAX loss falling
3.25 to 0.44 over 150 steps.

**Docs (26).** local-dev.md documents the recipe and the notebook;
demo-plan.md's failure section ends with the nuclear option: teach
from the notebook.

## Intentionally deferred, and why

- **The notebook duplicates app logic on purpose.** compute_reward,
  the dataset builders, and the templates exist in the api and again
  in the notebook. Standalone was the requirement ("anyone grabbing it
  would have missed little"), and importing from the api package would
  break `--sandbox`. The cost is drift risk; see tech debt.
- **Not in the WASM export list.** It trains with JAX and loads local
  models; pyodide can do neither. Deliberate, commented in the
  Justfile.
- **Gated cells are untested against live providers**, same standing
  caveat as the app: the fal calls, the VLM judge, and the Modal
  sketch follow the same request shapes the api uses (which were
  verified against mocks), but nobody has paid for a real call yet.
- **Sections still do not drag-to-rearrange.** Collapse + resize
  covered the actual complaint (unreachable Start button); drag
  ordering needs persisted per-user layout state and was not worth it
  this pass.

## Known issues / tech debt

- Notebook/app drift: if a snippet in `web/src/lib/snippets.ts` or a
  reward rule in the api changes, `notebooks/full-session.py` will not
  notice. There is no shared source. Grep for the constant you changed.
- The notebook's `sft_path` bridge is cwd-relative. Launched from
  anywhere but repo root it silently uses the $TMPDIR fallback. The
  header comment says to run from the repo, but nothing enforces it.
- First `just session-notebook` run downloads ~150MB of wheels
  (jaxlib alone is 81MB). Warm it before the session like everything
  else.
- Everything from the last handover still stands: synchronous fal
  polling, audio model cache lost on --reload, duplicate attendee
  names, ACE-Step payload guess.

## What the next phase should tackle first

1. Run the notebook once with real OPENAI_API_KEY and FAL_KEY: the
   opponent loop, the FLUX call, the VLM judge, and the LTX call all
   have never seen a live provider.
2. The same real-provider rehearsal for the app itself (carried over
   from last handover, still not done).
3. Consider `marimo export html` of the executed notebook into docs or
   the repo so attendees without uv can at least read it rendered.

## Gotchas

- marimo cell-level names are globally unique across the notebook;
  underscore-prefixed names are cell-local. The notebook leans on `_`
  prefixes heavily (`_r`, `_source`) to avoid collisions. If you add a
  cell and marimo complains about redefinition, that is why.
- Validating a marimo notebook headless is just `uv run <file>` (the
  `app.run()` in `__main__` executes every cell in dependency order
  and raises on error), plus `importlib` + `app.run()` in a probe
  script when you want to inspect the defs it produced.
- flax.nnx optimizers now require `wrt=nnx.Param`
  (`nnx.Optimizer(model, optax.adamw(...), wrt=nnx.Param)`) and
  `optimizer.update(model, grads)` takes the model first. Older
  snippets on the internet fail loudly.
- The tooltip fix (`pointer-events: auto` on h3) is load-bearing in
  two stylesheets: WorkspacePanel.css and ModalityPanel.css. Removing
  either regresses hover outside edit mode.
- The collapsible sections' localStorage keys are per-section, not
  per-user. Two people on the same browser share layout. Nobody will
  ever notice, but you might, in tests: a collapsed section from a
  previous run hides the button you are looking for.
