# Learning guide: the whiteboard learns to talk back

Last batch made your content survive. This one makes the app do
things: play against a model, narrate the game, generate images and
sounds, and run notebooks in every attendee's browser. The theme
underneath is one idea repeated: the app never knows which engine did
the work.

## The opponent goes through the same door you do

Click Start game, move a pawn, and gpt-5.5-mini answers. Here's the
design question worth chewing: the model's move could have taken a
privileged path, a special "apply this move" function that trusts the
model. Instead `model_move` funnels the reply through the exact same
`make_move` the board uses for humans. Why bother?

Because the model is not trustworthy, and that's the curriculum. When
it picks an illegal move, the environment rejects it, records reward
-1, and the board doesn't budge. Your RL slide just performed itself
on stage with a live model in the failure role. A privileged path
would have hidden the best moment of the session. The parsing is
equally paranoid: the reply must be JSON with a `move` that matches
UCI syntax, fenced or not, and anything else raises rather than
guesses. Never let a chatty model improvise your state transitions.

The endpoint is plain OpenAI-compatible chat completions, configured
entirely by environment: `OPENAI_BASE_URL`, `OPENAI_MODEL`,
`OPENAI_API_KEY` in your `.env`. When you swap to a Hugging Face
router next month, you will edit two lines and no code. One quiet
trick in the client: it asks for JSON mode, and if the endpoint
rejects the parameter with a 400, retries once without it. Compatible
endpoints are compatible the way in-laws are family.

## One file, three consumers

The Export dataset button writes
`data/processed/text/chess_sft.jsonl`: every game in the room,
rendered as prompt/completion pairs with the same template the
prompt_template snippet teaches. Now trace who reads it. The Unsloth
snippet loads it. The Axolotl YAML points at it. The notebook fetches
it over HTTP and shows you the rows. That is the whole "from playing
to training" story with zero hand-waving, and it's why the export
path is spelled out in the snippets instead of a placeholder like
`your_data.jsonl`. Placeholders are where workshop credibility goes
to die.

Question to sit with: why does the export rebuild the whole file from
the database every time instead of appending? Because the database is
the source of truth and the file is a view. Append-only files drift;
regenerated views cannot. It's the same reasoning as the canvas
snapshot, one level down.

## Allowlists, or: the frontend orders from a menu

The generate panels send `{"model": "flux-2-klein"}`, a short key,
never `fal-ai/whatever/i/found`. The backend maps keys to real model
ids through a catalog in one pure module. Why does this matter for a
workshop app with no auth? Because the alternative is your backend
happily forwarding arbitrary model ids, with your billing key
attached, to whatever endpoint an attendee's curl command names. The
menu is not bureaucracy, it's the bill.

Same shape for audio, with a twist: `audio.generate` dispatches by
model to a local engine (musicgen through transformers, stable-audio
through diffusers) or to fal, inside the runner. The UI cannot tell
which engine answered, which is the point, and has been since the
job-runner abstraction landed in phase 07. The new engines just
walked in through the door the architecture had already built.

Also worth noticing: generated files are downloaded from fal and
served from your own backend. fal's URLs expire; your demo replays
next week should not.

## Notebooks in the browser, physics included

Every technical page now embeds a marimo notebook compiled to WASM.
Attendees get real Python, numpy, pandas, matplotlib, running in
their own tab, no setup, no server, no queue. The board-sound
notebook synthesizes a capture click from sine waves and shows the
spectrogram. That's the audio page's entire thesis in one scrollable
panel.

The constraint to respect: pyodide cannot run torch. So the notebooks
teach data preparation and evaluation, the parts that fit in 2GB of
browser memory, and the actual training lives in the snippets and in
your Live notebook. That split is honest: browsers explore, GPUs
train. Your presenter client gets a Browser/Live toggle for exactly
this reason; Live embeds the marimo server on your machine, where
your RTX does the heavy lifting.

One bug worth retelling. When the WASM export is missing, the iframe
should say "run just notebooks". The first implementation checked the
HTTP status, and vite cheerfully answered 200 for the missing path,
because dev servers answer every unknown path with the app itself, for
SPA routing. Result: the app rendered inside its own notebook panel,
which rendered its own notebook panel, which... The fix checks the
response body for marimo's markup. Status codes tell you a server
answered; they don't tell you who.

## What to poke at

Set your keys in `.env`, `just start`, and play a full game against
the model watching the Analysis panel map your opening to a Monday
standup. Export, open the notebook, watch your rows arrive. Then break
something: unset FAL_KEY and note that Generate disables with a hint
instead of erroring; feed the model an impossible position and watch
the 502 explain itself. Apps built for a live room should fail like a
colleague, not like a stack trace.
