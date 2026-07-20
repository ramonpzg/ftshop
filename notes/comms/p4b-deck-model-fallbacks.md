# Supplemental phase prompt: deck model fallbacks

Use this prompt after the phase 35 deck system and teaching flow are accepted,
and before phase 36 release readiness.

## Prompt

You are implementing a supplemental deck-resilience phase for
`euro-scipy-chess-studio`. Build a small set of Slidev components that can
show real text, image, audio, and video model outputs when the collaborative
whiteboard is unavailable. Each comparison can switch explicitly between
named execution profiles. A profile binds one endpoint, credential source,
model, and capability set; selecting it changes the whole routing decision,
not just the model string.

This is not another application inside the deck. It is a presenter-controlled
fallback and comparison surface. Keep the implementation narrow, reuse the
existing job and artifact boundaries, and preserve the accepted deck design.

### Branch and boundaries

- Start from the accepted phase 35 result and create
  `phase-35b-deck-model-fallbacks`.
- Read `AGENTS.md`, all of `CLAUDE.md`, `docs/architecture.md`,
  `docs/session-plan.md`, `docs/demo-plan.md`, `docs/deck-plan.md`, and the
  accepted phase 33 through 35 handovers before editing.
- Inspect the current deck components, backend generation registry, artifact
  schema, cached fixtures, model configuration, and the `just start-gemma`
  workflow before choosing new interfaces.
- Preserve unrelated work. Do not read, edit, export, regenerate, or resolve
  anything under `notebooks/` or `web/public/notebooks/`.
- Do not redesign the deck, whiteboard, or session order. Do not add a general
  dashboard, provider-management screen, prompt editor, or model playground.
- Commit coherent, tested increments and push the branch. Do not merge it.
  Finish with no phase-owned uncommitted files.

### 1. Keep model access behind the backend

Deck components must not call OpenAI, fal, Hugging Face, llama.cpp, or another
provider directly. They must not receive API keys, provider tokens, or raw
provider URLs in browser code. Use the FastAPI backend through the deck's
same-origin `/api` proxy.

Extend the existing actions, job runners, artifact storage, and capability
registry where possible. Provider differences belong in data or runner
boundaries. Actions orchestrate. Calculations construct requests, normalize
results, and compare outputs. Vue components render and dispatch commands.

Define one small backend contract shared by the deck components and the
whiteboard's existing model picker. It should make these facts explicit:

- modality: text, image, audio, or video;
- execution source: local or API;
- concrete model ID and revision where available;
- input or saved input ID;
- status: ready, running, complete, unavailable, or failed;
- provenance: live or cached;
- artifact and evaluation metadata;
- duration, seed, and provider request ID when those values exist.

Do not flatten incompatible media into one string response. Share lifecycle
and provenance fields while keeping typed modality payloads.

### 2. Route through named provider profiles

Replace the current single-endpoint-plus-model-list assumption with a typed,
server-side profile registry. The initial text profiles are:

- `luna`: label `Luna (OpenAI API)`, OpenAI Chat Completions endpoint, model
  `gpt-5.6-luna`;
- `gemma-local`: label `Gemma 4 E2B (local)`, llama.cpp Chat Completions
  endpoint at `http://127.0.0.1:8020/v1`, model alias
  `gemma-4-2b-local`.

Environment configuration may override the endpoint, model, and credential
source for a profile without changing browser code. Do not send endpoint URLs,
credential environment-variable names, or secrets to either frontend. Expose
only a safe projection: stable profile ID, label, execution source, concrete
model ID, availability, and relevant capabilities.

The presenter-facing control is one compact dropdown. Its value is the stable
profile ID. Selecting an option atomically chooses that profile's endpoint,
credential, model, and capabilities. Do not use separate provider and model
controls, accept arbitrary endpoint URLs from the browser, or infer an endpoint
from a model-name prefix. Changing the dropdown must not start generation.

Use the same safe profile list and profile IDs in the whiteboard's timed-game
picker and the deck comparison components. Persist the selected profile ID
with a game, attempt, job, or artifact wherever it affects execution, alongside
the concrete resolved model already recorded for provenance. Existing rows
without a profile migrate to an explicit `unknown` value rather than a guess.

Starting local Gemma and selecting it are separate operations. The workshop
runbook starts `just start-gemma` before the session and leaves it warm, while
the dropdown determines whether a request goes to it. Do not require a backend
restart to move between Luna and Gemma. Update `just start-gemma` to use port
8020 and text-only serving; keep it separate from `just start`.

### 3. Build one compact comparison surface per modality

Use one component family with concept-specific renderers rather than four
unrelated mini-apps. The named-profile dropdown is required. It must be
keyboard accessible, have a stable width, and never change selection on its
own. Switching profile changes the selected saved result immediately and does
not start a paid or expensive generation.

Each surface shows:

- the exact common input;
- named profile selection and its Local or API source;
- concrete model name;
- cached or live provenance;
- the output in its native form;
- two or three relevant measurements;
- a short unavailable or failed state that preserves the cached result.

Use the same input on both sides wherever the APIs permit it. When seeds,
sampling controls, duration, or media dimensions are not equivalent, display
that difference rather than claiming a controlled comparison.

Implement these four presenter cases:

**Text.** Send one chess position, its legal moves, and one JSON contract to
local Gemma 4 through llama.cpp and to the configured API model, initially
Luna. Show the raw response, parsed move, legality, short reason, and latency.
Reuse the existing Chat Completions client and legality calculation. Do not
introduce the Responses API.

**Image.** Show the same chess-piece style prompt through the configured local
and API image runners. Render matched base/adapted or local/API images at a
stable aspect ratio with model, seed, dimensions, and the accepted identity
and style measurements. If no honest local image runner exists in the
accepted codebase, implement the typed unavailable state and a pinned local
fixture. Do not label a remote provider as local to satisfy the toggle.

**Audio.** Use the same short prompt and requested duration. Local mode uses
the accepted MusicGen or Stable Audio runner. API mode uses the accepted audio
provider runner. Provide native audio controls plus duration, clipping, and
one compact spectrogram. Do not autoplay.

**Video.** Both modes receive the same detailed real-world scene prompt saved
from Luna's game mapping. The clip must depict the real-world case, never a
chess move or pieces on a board. Render a poster before playback and show
duration, resolution, model, case adherence, and subject continuity. Do not
autoplay or generate on slide entry. If local LTX inference is not practical
on the workshop machine, say unavailable and retain the pinned local fixture.

Use the model IDs and runtime choices accepted by the preceding phases. Do
not guess a new current model name in copy or fixtures. Configuration must
remain environment-driven.

### 4. Make the fallback independent of a live demo

Every modality needs one reviewed Local result and one reviewed API result
available before the session. Store a small manifest with exact input,
provenance, model, revision, parameters, output path, evaluation values, and
license/source notes. Bundle only presentation-sized media with the deck or
another path that survives a whiteboard failure. Do not point fallback cards
at temporary job URLs.

The default slide state uses these pinned results. A presenter-only `Run live`
command may replace the selected result after explicit activation. It must
never run on mount, slide entry, mode change, reconnect, or attendee view.

Add a backend cost guard such as `DECK_LIVE_MODE=1`, default off. API and heavy
local jobs requested from the deck must fail closed when the guard is off.
The component should retain its cached output and state the failure tersely.
Do not rely on a hidden button as authorization.

The deck must still present useful results in these cases:

1. whiteboard frontend unavailable, backend and deck running;
2. backend unavailable, deck running;
3. local model unavailable;
4. API key missing or provider unavailable;
5. a live request fails after a cached result has rendered.

### 5. Keep presenter control and deck pacing

Place each component only on the accepted outcome or modality slide where it
replaces a placeholder or makes the existing comparison concrete. Preserve
the slide's title, argument, click budget, speaker notes, and 16:9 geometry.

Use Slidev clicks or explicit component controls. No automatic cycling,
polling, generation, playback, or mode switching except the existing LiveRoom
polling required for its purpose. Honour reduced motion. Returning to a slide
must restore a deterministic cached state rather than retaining an accidental
half-run.

Keep visible copy direct and factual. Use `Local`, `API`, `Run live`,
`Cached`, `Unavailable`, and concrete model names. Do not add slogans, puns,
AI hype, fake score precision, or copy explaining how impressive the output
is.

### Tests and acceptance

Add focused tests at calculation, backend, and deck-component boundaries.
At minimum prove:

1. Profile switching changes the endpoint and model together, changes only the
   selected result, and never starts a job.
2. The whiteboard and deck receive the same safe profile IDs and labels; neither
   frontend receives endpoints or credential details.
3. Both text profiles receive the same position, legal-move list, and JSON
   contract, and legality is calculated rather than trusted from the model.
4. No browser bundle or request exposes provider credentials.
5. `Run live` is rejected while `DECK_LIVE_MODE` is off and runs exactly one
   job when enabled.
6. Cached image, audio, and video remain usable with the backend down.
7. Failed live work leaves the cached result visible with accurate provenance.
8. Audio and video never autoplay.
9. Long model IDs, raw text replies, errors, and metadata fit at 1920x1080,
   1440x900, and 1280x720 without overlap.

Exercise at least one real local Gemma call through `just start-gemma` and one
real configured API text call before claiming the live comparison works. For
paid media paths, a pre-generated artifact with recorded request ID and exact
parameters is acceptable; do not spend money merely to make a test green.

Run `just lint`, `just typecheck`, `just test`, the deck production build, and
the relevant Playwright checks. Capture screenshots of every modality in both
modes and one backend-unavailable state. Record paths in the handover.

### Documentation and final report

Update `docs/deck-plan.md`, `docs/demo-plan.md`, and `docs/local-dev.md` with:

- the component and backend contract;
- the pinned fixture manifest and provenance rules;
- model and endpoint configuration;
- the live-mode cost guard;
- the exact fallback sequence when the whiteboard or backend fails;
- a rehearsal checklist proving every cached artifact opens offline.

Create:

- `notes/ai/phase-35b-deck-model-fallbacks.md`
- `notes/hu/phase-35b-deck-model-fallbacks.md`

The handover must state which modes are genuinely local, which are API-backed,
which use pinned fixtures, what was exercised live, and what remains hardware
or provider dependent. The learning guide must explain why source selection
is a backend concern, why toggling must not trigger generation, and why cached
evidence is part of workshop correctness rather than a decorative fallback.

Finish with a concise inventory of components, endpoints, fixtures, tests,
screenshots, live calls made, paid calls avoided, and deferred work.
