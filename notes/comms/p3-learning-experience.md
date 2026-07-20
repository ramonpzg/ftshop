# Phase 3 prompt: complete learning experience

Use this prompt only after phases 32 and 33 have been reviewed and accepted.

## Prompt

You are implementing phase 34 of `euro-scipy-chess-studio`: turn the reliable,
truthful workshop machinery into a complete learning experience that fits a
real 90-minute session.

The workshop's central sentence is "pairs in, adapter out, eval always." The
board and deck currently state that loop without making the adapter and its
evidence visible. Cached artifacts are often metadata rather than inspectable
media, evaluation values lack teaching context, and the documented agenda
uses all 90 minutes before questions or failures.

This phase must make the educational loop observable. It must not implement or
edit the notebook. The notebook is now a standalone Jupyter asset, not Marimo
and not a tldraw iframe. Cached training is acceptable. Invisible training is
not.

Phase 33 now provides durable attempts, model/checkpoint-scoped metrics,
`run_id`, sample IDs, and `position_set_id`. It does not provide the benchmark
runner that forces a base checkpoint and an adapted checkpoint through the
same frozen inputs. Organic games from two models are not a paired benchmark
merely because both produced metrics. Building that honest paired path is the
first responsibility of this phase.

### Branch and boundaries

- Start from the accepted phase 33 result and create
  `phase-34-learning-experience`.
- Read `AGENTS.md`, the final tone guide in `CLAUDE.md`, architecture, session,
  demo, deck plan, and phase 32-33 handovers before editing.
- Preserve unrelated changes. Do not read, edit, format, export, regenerate,
  or resolve `notebooks/` or `web/public/notebooks/`.
- Commit coherent, tested increments throughout the phase. Push the phase
  branch, finish with no relevant untracked or uncommitted files, and do not
  merge it into `main`. Ramon reviews the summary and diff first.
- Do not perform the phase 35 visual redesign. Add only the UI needed to make
  the teaching flow usable, following the current visual language.
- Do not perform the broad phase 36 architecture refactor. New functionality
  must still follow actions/calculations/data from the start.
- Preserve phase 33's Chat Completions, transaction, structured 409, dataset,
  and metric contracts. Do not replace them while building the learning UI.
  `make_move` checks `expire_if_over` inside `BEGIN IMMEDIATE`, before any move
  writes, so a wait for the lock cannot carry a move past its deadline.
- Do not add a notebook panel or iframe. Where the run of show uses Jupyter,
  describe a deliberate switch to a separately opened local notebook and a
  return to the board or deck only when useful.
- Assume up to 40 attendees and venue Internet that may disconnect after a few
  idle minutes and require a captive-portal login. No attendee should need an
  API key or provider login. No core outcome may depend on 40 simultaneous
  cloud requests. Keep paid or remote generation presenter-controlled and
  optional, with the reviewed local result already visible.

### 1. Build one complete adaptation evidence chain

Implement a vertical slice that the presenter can run from the board without
opening a shell:

1. Select or freeze a training dataset snapshot with row count, source games,
   participant approval state, schema version, and content hash. Apply phase
   33's training-eligibility rule: fallback moves stay in the audit archive but
   never enter the SFT snapshot. Keep raw and participant-approved scenario
   mappings distinguishable.
2. Select a small, legible training configuration showing base model, method,
   adapter parameters, seed, and intended output task.
3. Start a training job through the existing job registry abstraction. A
   replayed or cached result is acceptable and preferred to a fragile live
   training dependency, but the UI must say exactly which it is.
4. Produce durable adapter metadata and artifact provenance, including base
   model, dataset hash, config hash, runner, creation time, and limitations.
5. Freeze a separate evaluation suite with durable input IDs, the exact FEN or
   prompt for every example, schema/prompt version, multiplicities, and content
   hash. Run both base and adapted checkpoints against that one suite. Persist
   the resolved model and a non-null checkpoint on every benchmark attempt so
   phase 33's scoped calculations operate on real evidence. Mark whether each
   output came from a live call or a replayed fixture; replay must not invent a
   provider request ID or pose as a live model attempt.
6. Present the before/after examples, metric delta, sample size, and any
   regressions together. Compute a delta only when both results have the same
   non-null `position_set_id`, evaluation-suite hash, and prompt contract. A
   mismatch is `Not comparable`, not a number.

The frontend asks to run a job type and renders the result. It must not know
which runner produced it. Do not add a decorative Train button that skips the
registry, returns a hardcoded success object, or cannot be traced to a dataset
and configuration.

Training-data identity and evaluation-suite identity are separate. Do not
train on the held-out comparison examples, derive a comparison from two
organic game histories, or manufacture matching `position_set_id` values.
Phase 33 hashes the exact input multiset, with duplicate positions preserved;
reuse that calculation rather than inventing a second hash.

Make the difference between a base checkpoint, adapter, merged checkpoint,
inference model alias, and illustrative fixture explicit. Use short labels and
one compact provenance view rather than explanatory walls of text.

For Gemma, keep the existing distinction concrete:
`google/gemma-4-E2B-it-qat-q4_0-gguf` is the llama.cpp inference repository and
`gemma-4-2b-local` is its serving alias;
`google/gemma-4-E2B-it-qat-q4_0-unquantized` is the training starting point.
Do not claim that TRL or Axolotl trained the GGUF directly. This phase records
the resolved model and checkpoint but does not build the Local/API profile
dropdown owned by phase 35b.

The text modality is the full vertical slice. For image, audio, and video,
show the same conceptual chain with an appropriately scoped cached adapter or
artifact if real training is impractical. The parallel should be visible
without pretending the implementation depth is identical.

### 2. Replace metadata-only fixtures with inspectable artifacts

Audit every cached artifact named in `docs/demo-plan.md`. A presenter following
the plan must be able to reveal the thing the plan describes:

- Image needs a real before and after pair at useful inspection size.
- Audio needs a playable file with duration and a useful compact waveform or
  spectrogram representation.
- Video needs a playable clip or a deliberately lightweight local media file
  with poster, duration, and frame evidence.
- Text needs concrete base/adapted responses and the source prompts.

Use generated or appropriately licensed media. Record source, creator or
generation method, license, model, prompt where applicable, and any editing.
Store workshop-critical fallbacks locally so expired provider URLs or venue
network failure do not break them. Update `docs/licenses.md` or the existing
license inventory.

MusicGen is sufficient for the local audio evidence in this phase. Stable
Audio may remain an optional, already-downloaded alternative; do not make its
gated download, license check, or runtime part of the workshop-critical path.

Artifact panels should prioritize the artifact itself. Put raw provider JSON,
hashes, and detailed provenance behind a compact disclosure. Provide loading,
missing, unsupported-media, and playback-failure states.

### 3. Make evaluation panels teach comparison

Use the phase 33 metric metadata to show:

- value and unit;
- higher/lower direction;
- numerator and denominator or sample count;
- base value, adapted value, and signed delta when comparing;
- computed versus cached source;
- dataset/eval version;
- a concise definition and cached-value limitation.

Keep the default panel scannable. Definitions and provenance may expand on
demand. Do not use color alone to communicate improvement, regression,
computed, or cached state. Handle unavailable and zero-sample metrics
explicitly.

Add one example where adaptation improves the target metric but regresses
something else. A top educational experience should teach tradeoffs, not make
every result look conveniently better.

### 4. Rewrite the run of show around outcomes first

Define three or four concrete outcomes participants can demonstrate by the
end. Then rebuild `docs/session-plan.md` and `docs/demo-plan.md` around a
70-75 minute core plus 15-20 minutes of controlled flex, setup, questions, and
recovery. Keep the advertised session length at 90 minutes.

Use this provisional narrative order unless Ramon changes it during review:

1. A compact motivation: why fine-tune instead of only prompting or using a
   larger hosted model.
2. Why chess is a useful shared domain, Ramon's route back into chess, and the
   minimum rules and notation needed by people who do not play.
3. A quick map of interesting fine-tuning outcomes in chess, including move
   prediction, commentary, personalized instruction, style, sound, and the
   real-world scenario dataset.
4. The outcome-first demo sequence. Show the text, image, audio, and video
   results before teaching their implementation details. Make base versus
   adapted behavior visible where an adapted result exists.
5. Decompose what the room just saw: paired data, preparation, base model,
   adapter/training choice, inference, evaluation, and modality-specific
   failure modes.
6. Participant practice, comparison, and close.

Map that narrative onto the actual asset order. Start in the deck for the
motivation, minimum chess context, and outcome previews. Move to the
whiteboard for the shared game, dataset, and visible adaptation evidence.
Finish in the separately opened Jupyter notebook for the pragmatic code
walkthrough and participant work, referring back to a deck slide or
whiteboard frame only when it removes repetition. Do not finish by returning
to the deck merely to restate the close.

Do not open with a long transformer history, framework survey, or LoRA
mechanics before participants have seen what adaptation changes. The opening
must motivate without becoming marketing copy. Keep sections modular so Ramon
can adjust the order after this engineering pass without rebuilding every
slide and presenter transition.

For every segment, specify:

- target duration and hard stop;
- what participants predict before the action;
- what they run or contribute;
- the one artifact or comparison everyone inspects;
- the explanation that closes the loop;
- an optional cut when the room runs late;
- the fallback when a provider or attendee device fails.

Make active participation honest. If image drawings become paired examples,
persist and inspect them. If audio or video is presenter-led because 40 cloud
requests would be slow or expensive, say so and give attendees a smaller
prediction or comparison task instead of pretending all sections are equally
hands-on. Default all provider-backed media work to that presenter-led model;
the room can compare the pinned outputs without contacting the provider.

Include all app/deck transitions and presenter controls in one run of show.
Remove contradictions such as a five-minute opening whose listed speaking
beats already exceed five minutes. Keep Ramon's intentional Queen's Gambit
beat and any explicit content placeholders. Phase 35 will polish wording and
visual rhythm; this phase fixes instructional structure and timing.

### Tests and acceptance

Add real tests for dataset snapshot identity and training eligibility, held-out
evaluation-suite identity, job registry routing, adapter provenance,
checkpoint-tagged attempts, base/adapted comparison scope, refusal to compute
a delta for mismatched position sets or prompt contracts, honest live/replayed
provenance, cached media availability, and eval panel states. Do not assert
only that a button rendered.

Run `just lint`, `just typecheck`, `just test`, and relevant E2E checks. Build
the deck if technical content changed. Perform a manual presenter walkthrough
using no provider keys and prove that every core artifact remains available.
Then exercise one configured live generation path if credentials are present;
absence of keys must not block completion.

Walk through the attendee actions assuming a full room. Prove that the core
path does not ask attendees to authenticate with a provider and does not
multiply one presenter's remote generation call into one request per browser.

Time the core walkthrough rather than estimating it from headings. Record the
measured duration, what was skipped, and where the presenter waited for the
system.

### Documentation and final report

Update architecture, session, demo, local-development, artifact-license, and
fixture provenance documentation. Ensure cached-training language is accurate
everywhere.

Create:

- `notes/ai/phase-34-learning-experience.md`
- `notes/hu/phase-34-learning-experience.md`

The handover must enumerate the full evidence chain, cached versus live
boundaries, media provenance, timed rehearsal result, cut list, standalone
Jupyter boundary, full-room/offline assumptions, and the exact outcome-first
narrative used. The learning guide should ask why an adapter without a dataset
hash is not reproducible and why a metric delta without a matching frozen eval
set is mostly decoration.

Finish with a concise summary and a table of each modality's participant
action, visible artifact, evaluation, live dependency, and fallback.
