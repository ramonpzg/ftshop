# Handover: phases 19-23, the app goes live

Written 2026-07-06, second batch of the review branch. Read
notes/ai/phases-09-17-review-upgrade-persistence.md first; this builds
on it.

## What was built

**Workspace relayout and polish (19).** Mini IDE owns the full right
column with working vertical scroll (the @uiw/react-codemirror wrapper
div has no intrinsic height; without `flex:1; min-height:0` on it the
editor grows past the window and clipping eats the scroll). Grid is
named template areas at 1160x800; explicit dark text everywhere; one
accent color per section icon; colored left borders key the six dataset
row shapes; native `title` tooltips on every section header (custom
tooltips would clip against the sections' `overflow: hidden`). Pages
2-5 seed two explainer frames each at x>=1400, y<1400, provably clear
of the workspace band (y>=1500); a pageSeeds test asserts the geometry.

**Model opponent + analysis (20).** `data/llm_client.py` speaks any
OpenAI-compatible chat-completions endpoint (OPENAI_API_KEY / BASE_URL
/ MODEL; repo-root .env loaded at startup without overriding the
shell). `actions/game.py`: model_move runs the model's choice through
the same make_move path as a human, so illegal model moves record with
reward -1 and do not advance the board, deliberately. assess_position
returns {assessment, real_world, model}. Frontend: Start game arms
auto-reply after every legal user move; Analysis section refreshes per
exchange; Assess position button for solo play; everything disables
with a hint when unconfigured (GET /llm/status).

**Dataset export (21).** POST /datasets/text/export writes all
workspaces' fen_legal_moves_to_move rows as prompt/completion JSONL to
data/processed/text/chess_sft.jsonl (atomic, gitignored) and GET serves
it. The Unsloth and Axolotl snippets and the chess-machine notebook all
point at that exact file.

**Snippets (21).** fine_tune is now Unsloth (`FastModel`,
`unsloth/gemma-4-E2B-it`; Gemma 4 shipped 2026-03, E2B is the small
one, there is no plain 2B). New: axolotl_config (yaml, needs
@codemirror/lang-yaml and the snippet `language` field) and jax_train
(flax.nnx, the only snippet that trains on a laptop CPU). Unsloth
Studio tab-link opens localhost:8888 (`unsloth studio -p 8888`).

**Generation (22).** image.generate / video.generate run on fal's
queue API (`data/fal_client.py`; FAL_KEY; FAL_QUEUE_BASE override for
tests). Model allowlists in `calculations/generation.py`: FLUX.2 Klein
4B + schnell; LTX 2.3 fast + Veo 3.1 fast (Veo wants duration as a
string, LTX as an int). Outputs download to artifacts/generated
(gitignored) and serve at /artifacts/files/{name}. audio.generate
dispatches by model inside `jobs/audio_runner.py`: musicgen-small
(transformers) and stable-audio-open-1.0 (diffusers, gated, HF_TOKEN)
locally, ACE-Step on fal. Local audio deps are the `audio` uv extra
(`just install-audio`); without them the route 503s with that exact
instruction. run_job now persists the job config only after the runner
succeeds.

**Notebooks (23).** notebooks/*.py are marimo sources, one per
technical page; `just notebooks` exports them WASM into
web/public/notebooks (gitignored, ~27MB each). NotebookShapeUtil embeds
them per page at (1400, 800). Presenter clients get a Browser/Live
toggle; Live points at a local marimo server (default localhost:2718,
URL in localStorage). The build probe fetches the export and checks the
body for "marimo" because vite's SPA fallback answers 200 text/html
for missing paths and the iframe would otherwise show the app inside
itself.

## Intentionally deferred, and why

- **ACE-Step payload shape on fal is unverified.** The generic
  output-url extractor covers the likely response shapes, but the
  input params ({prompt, duration}) are a best guess; expect to tweak
  on the first real call. Image and video shapes were verified against
  fal's live docs.
- **Opponent state is client-side.** Reload and you click Start game
  again. A workspaces.opponent column was skipped to avoid a schema
  migration for a toggle.
- **The workspace does not stream analysis.** One request per
  exchange, no token streaming. Fine at gpt-5.5-mini latency.
- **Pyodide loads from its CDN.** marimo 0.23 exposes no self-host
  knob for it. Warm the cache before the session; the Live notebook is
  the offline fallback.
- **No game-over detection surfaced** (unchanged from last batch); the
  model opponent raises "no legal moves; the game is over" as a 502
  rather than a friendly state.

## Known issues / tech debt

- fal polling is synchronous inside the request thread: a video job
  holds one FastAPI worker for a minute or two. Fine for one presenter;
  wrong if attendees generate video en masse.
- Local audio pipelines cache in the API process; `--reload` restarts
  drop the cache and the next generation pays the model load again.
- The first musicgen call downloads ~2.4GB; stable-audio ~4.6GB.
  Pre-pull both before the session (`just install-audio`, then one
  generation each).
- The attendee list still accumulates duplicate names when the same
  person joins from a second browser.

## What the next phase should tackle first

1. Run `just notebooks` and `just install-audio` on the real machine,
   pre-pull models, and do one real fal image + video call (checks the
   ACE-Step guess too).
2. A real end-to-end rehearsal against api.openai.com with
   gpt-5.5-mini: latency will set the pace of the Start game beat.
3. Consider async job execution for video generation if attendees will
   trigger it.

## Gotchas

- The `.env` loader never overrides shell variables. If a key
  mysteriously will not change, check the shell first.
- FalRunner and AudioRunner are exercised through monkeypatched fakes
  in tests; FAL_QUEUE_BASE + the two mock servers in this session's
  scratchpad show how to fake both providers end to end.
- Playwright note: tldraw shapes outside the viewport cannot be
  dblclicked; press Shift+1 (zoom to fit) first.
- The notebook iframe steals wheel events only in edit mode, same as
  every other embedded panel (canScroll).
- `mo.image("/pieces/wN.svg")` in the WASM notebook works because the
  export is served same-origin; if a notebook moves to marimo.app that
  path breaks (different origin).
