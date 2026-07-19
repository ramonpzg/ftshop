# Handover: standalone notebook, Gemma 4, and real-world video

Written 2026-07-19. This phase turns the workshop Markdown export into a
Zed-compatible Python notebook, applies the first content review, updates the
Gemma baseline, and changes the video lesson from literal chess footage to a
real-world scene derived from a game.

## What was built

`notebooks/full-session3.py` is a Jupytext percent-format script. Zed can run
its 62 cells with the root `.venv` and the `ftshop` kernel. It is standalone,
offline by default, and uses ordinary Python displays. There is no Marimo
state or conditional UI machinery. The low-level training example uses JAX
directly, including `jax.value_and_grad`; it does not use Flax or Optax.

The notebook now separates the two Gemma artifacts. Local inference uses
`google/gemma-4-E2B-it-qat-q4_0-gguf`. TRL and Axolotl examples use the
matching `google/gemma-4-E2B-it-qat-q4_0-unquantized` source because those
trainers do not consume the deployment GGUF as a normal training checkpoint.
The deck, snippets, README, canvas copy, and session plans use the same rule.

Game analysis has a three-field contract: `assessment`, `real_world`, and
`video_prompt`. Luna reads the move history and position, explains the
real-world relationship, then writes one detailed filmable prompt. That prompt
contains the setting, visible people, physical action, camera, lighting, and
sound. It explicitly excludes chessboards, pieces, notation, and moves.

The API can use separate `VIDEO_PROMPT_API_KEY`, `VIDEO_PROMPT_BASE_URL`, and
`VIDEO_PROMPT_MODEL` values, falling back to the opponent provider settings.
This allows local Gemma play and hosted Luna scene writing in the same process.
The workspace shows the resulting prompt with a copy action. Cached video
fixtures, evaluations, page seeds, deck copy, and the authored canvas now
stage the same real-world release-room example.

## Intentionally deferred

- No provider request or video generation was run. The checked-in scene is an
  explicitly labelled offline fixture, not a claimed Luna or LTX result.
- The source `notebooks/full-session.ipynb` and the working Markdown export
  were left untouched because Ramon is editing them concurrently.
- The notebook has not been renamed to the final public filename. Keeping
  `full-session3.py` avoids taking ownership of Ramon's working source before
  the content review is complete.
- A real generated clip still needs to replace the deterministic illustrative
  stand-in after the prompt and model choice settle.

## Known issues and debt

The provider schema is strict but semantic prompt requirements are enforced by
the system prompt, not a second validator. A model can return three non-empty
strings and still produce weak camera direction. That is an evaluation problem,
not a reason to hide more logic in the parser.

The video fixture filename remains `chess_moment.json` for compatibility even
though its content is now a real-world scenario. Rename it only with all job
lookup paths and tests in view.

Running the notebook as a plain script under a non-interactive Matplotlib
backend emits harmless `FigureCanvasAgg` warnings. Zed's Jupyter kernel renders
the figures inline and does not have this presentation issue.

## What the next phase should do first

Generate two or three clips from the saved scene prompt, preserve their exact
model settings, and choose one by case fidelity and subject continuity rather
than spectacle. Then replace the offline stand-in and record measured results.

After that, rehearse the notebook's presenter path against the available time.
The standalone reference can remain expansive, but the live path needs named
skip points and a measured duration.

## Gotchas

Do not set `OPENAI_BASE_URL` to llama.cpp and assume Luna will still work. Set
the three `VIDEO_PROMPT_*` variables when opponent and scene-writer providers
differ.

Do not pass the GGUF repository directly into the shown TRL or Axolotl flows.
Train from compatible weights, merge the adapter, then convert the result for
llama.cpp deployment.

The direct JAX example is intentionally small. It demonstrates differentiation
and parameter updates; it is not a claim that a Gemma fine-tune fits in one
notebook cell.
