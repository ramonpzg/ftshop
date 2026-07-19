# Learning guide: one game, two models, no wooden actors

This phase makes one boundary explicit. Gemma plays the game locally. Luna
turns the completed game into a real-world situation and writes the scene that
a video model will render. LTX does not need to know that chess was involved.
That is useful because video models are rather better at filming people in a
room than maintaining a legal board position while pieces teleport with great
confidence.

## Start with the contract

Open `api/src/euro_chess_studio/calculations/llm_prompts.py` and ask what would
happen if `real_world` and `video_prompt` were one field. The explanation of
the analogy and the production instructions would compete for detail. You
would also lose the ability to evaluate the intellectual mapping separately
from the clip's visual adherence. Three fields make three jobs visible:
diagnose the game, explain the case, stage the case.

Now ask why the parser checks types and non-empty strings but does not count
sentences or ban the word "chess". A stricter parser could reject obvious
mistakes, but it would turn prose quality into brittle string rules. The
system prompt sets the contract. Saved examples and clip evaluations measure
whether the model followed it. Parsing protects the transport boundary.
Evaluation protects the lesson. Confusing those produces impressive regular
expressions and unimpressive videos.

Follow the action into `api/src/euro_chess_studio/actions/game.py`. It gathers
the durable move history, asks the pure calculation module to construct the
messages, calls the data client, parses the reply, and returns the result.
Why is the Luna call not inside the route? Because HTTP is only one way to
trigger this action. Why is it not inside the prompt module? Because building
messages is deterministic while calling a provider is not. Actions,
calculations, and data each get one kind of reason to change.

## Two providers in one process

The ordinary `OPENAI_*` settings describe the chess opponent. The
`VIDEO_PROMPT_*` settings describe the scene writer and fall back to the first
set when both jobs use one endpoint. Consider the local workshop setup: a
llama.cpp server hosts Gemma, while Luna lives behind a hosted Chat Completions
endpoint. One global base URL cannot address both. Separate settings are less
magical and therefore easier to explain at a workshop, a quality that software
occasionally remembers to value.

What should happen if the video key is absent but the OpenAI key exists? The
fallback keeps the simple setup simple. What should happen if neither exists?
The data layer raises a configuration error before making a request. The unit
test in `api/tests/data/test_llm_client.py` records the more interesting case:
Gemma and Luna use different endpoints, keys, and model names without either
configuration leaking into the other.

## A file format is not a training method

The local model ID ends in `gguf`. That is the artifact served by llama.cpp.
The training snippets point to the matching unquantized QAT repository. Ask
why both IDs need to appear in the workshop instead of quietly swapping one
for the other. The answer is the lesson: deployment representation and
training source are different decisions. Hiding that distinction makes a
shorter slide and a longer debugging session.

The same restraint applies to the JAX example. It uses arrays, a small loss,
`jax.value_and_grad`, and an explicit parameter update. There is no Flax model
class and no Optax optimiser state. What does the example teach? Automatic
differentiation and an update step. What does it deliberately not teach? How
Gemma's full architecture, quantisation, adapter injection, and distributed
training fit together. A workshop cell should make one mechanism legible,
not impersonate an entire trainer stack.

## The notebook as a script

`notebooks/full-session3.py` uses `# %%` markers. Zed sends each region to the
`ftshop` Jupyter kernel, so ordinary imports, plots, audio, SVG boards, and
tables render inline. Read the file from top to bottom and notice that the
offline path is the default. Provider calls are functions the learner can run
deliberately, not branches scattered through every display cell.

Ask what a learner sees when no key is present. They still get the complete
argument, a labelled fixture, the data shapes, the metrics, and the training
ladder. A live service enriches the artifact instead of holding it hostage.
That matters in a conference room, where the network has its own presentation
schedule and rarely shares it in advance.

The video section now displays the mapping before the clip. The example game
becomes a rushed software release in a small operations room. Luna's scene
prompt specifies who is visible, what each person physically does, how the
camera moves, the light, and the sounds. The generated model receives only
that paragraph. If the clip fails, you can now ask a precise question: was the
case weak, was the scene underspecified, or did the video model ignore it?
That is a useful decomposition. "The chess video looks bad" was merely an
accurate complaint.
