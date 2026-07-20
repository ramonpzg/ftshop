# Handover: phase 34, complete learning experience

Written 2026-07-20 on branch `claude/p3-learning-experience-gvp2tq`
(the phase's designated working branch in this environment; the comms
README's `phase-34-learning-experience` name refers to the same phase).
Base: accepted `main` at 2b5477a, with phases 32 and 33 merged.

The phase's sentence: the loop "pairs in, adapter out, eval always" is
now observable end to end. Cached training exists and says it is
cached. Invisible training does not exist.

## The evidence chain, end to end

One honest path from play to comparison, every link durable:

1. **Dataset identity.** `dataset_snapshots` freezes the room's
   `fen_legal_moves_to_move` rows through the same `build_sft_rows` the
   export uses. Phase 33's eligibility rule applies at freeze time:
   fallback and unknown actors are counted in
   `excluded_ineligible_count`, never included. Scenario mappings ride
   along as separate raw and participant-approved counts. Rows are
   stored inline (`rows_json`) so a page reset cannot hollow out a
   snapshot. `content_hash` is the position-set recipe: sorted,
   duplicates preserved, sha256 prefix.
2. **Config identity.** `TRAINING_CONFIGS` in
   `calculations/adaptation.py` is a typed catalog (one entry,
   `text-gemma-lora-v1`) with `config_hash` over the full dict. It
   keeps the three Gemma roles distinct: base_model is the unquantized
   training start, inference_repo is the GGUF, serving_alias is
   `gemma-4-2b-local`. Nothing anywhere claims TRL trained the GGUF.
3. **Adapter provenance.** `adapters` records checkpoint label, base
   model, method, seed, output task, config id/hash/json, dataset
   snapshot id and content hash, runner, `result_source`
   (cached/live), limitations, created_at. `text.train_adapter` (local
   runner, ordinary registry) replays
   `artifacts/cached/text/train_adapter.json` and enforces three
   refusals: fixture config hash must match the selected config,
   fixture dataset hash must match the selected snapshot (so the
   cached result can never pose as training on the room's data), and
   no snapshot overlapping a held-out suite may train at all. A rerun
   over the same identity returns the existing adapter with
   `already_trained: true`.
4. **Evaluation-suite identity.** `eval_suites` freezes twelve
   held-out mid-opening positions with durable example ids, exact FEN,
   legal move list, rendered prompt, schema version, prompt contract
   (`sft-v1`, the training template's own version constant), content
   hash, and the suite's `position_set_id`. Example `ex-12` repeats
   `ex-01`'s position deliberately: multiplicity is data and hashes
   differently. Seeding asserts snapshot/suite disjointness and is
   idempotent by content hash.
5. **Benchmark runs.** `text.benchmark_eval` forces one checkpoint
   through the suite. Every reply becomes a `model_attempts` row with
   `task='benchmark_move'`, non-null `checkpoint`, the resolved model,
   `reply_source` live or replayed, `benchmark_run_id`,
   `suite_example_id`, and a null `workspace_id` (the column went
   nullable via a rebuild migration; benchmark evidence belongs to the
   room). Replay never invents request ids. Live runs (base only; the
   adapter has no serving path and the 409 says so) record real
   request ids and transport provenance; a transport failure stays out
   of every denominator, honestly shrinking that run's position set.
   Metrics are the phase 33 calculations plus the new
   `explanation_rate`, persisted with model/checkpoint/run_id/psid.
6. **Comparison.** `calculations/comparison.py` emits a signed delta
   with an improved/regressed/unchanged verdict only when suite hash,
   prompt contract, metric version, and non-null position-set ids all
   match. Anything else is "not comparable" with the reason, values
   still visible. `GET /adaptation/state` assembles everything the
   panel renders.

The numbers on the seeded chain: base 7/12 legal (0.58), 10/12 valid
JSON (0.83), 9/12 explanations (0.75); adapted 12/12, 12/12, 0/12.
Legality +0.42 improved, JSON +0.17 improved, explanation −0.75
regressed. The regression is the requested trade-off example and it is
data, not styling; the modality evidence fixtures each carry one too
(piece identity, clipping, frame detail).

## Cached versus live boundaries

- Training: always a cached replay, labelled `cached` on the artifact,
  the adapter row, and the panel. No live path exists; the UI says so
  in words next to the button.
- Benchmarks: replayed by default (works keyless); live is base-only,
  presenter-triggered, button exists only when `is_llm_configured()`.
  Live and replayed runs coexist as separate rows and never blend
  (model+checkpoint are part of eval identity).
- Modality evidence (image/audio/video): entirely cached fixtures with
  real local media; the adapter cards there are labelled illustrative.
- Cached eval numbers from phase 33 (centipawn loss and friends)
  unchanged, note rendered under the value.
- Generation jobs (`*.generate`, FAL) unchanged: presenter-controlled,
  optional, absent without keys.

## Media provenance

Eleven committed files under `artifacts/cached/media/` (~2.1 MB), all
generated in-repo by `api/src/euro_chess_studio/tools/make_media.py`
via `just make-media` (media extra: pillow, numpy, cairosvg, av),
deterministic seeds, byte-stable regeneration (verified twice).
Provenance is recorded in the tool docstring, per-fixture `provenance`
blocks, and docs/licenses.md ("Workshop media fixtures"):

- image: Cburnett wB.svg (CC BY-SA 3.0) rasterized clean, and restyled
  into watercolor washes with the linework composited back. CC BY-SA
  derivatives, attribution kept.
- audio: synthesized capture click; one motif rendered calm (90 bpm)
  and sharpened (132 bpm, tension notes, level ramp); waveform PNGs of
  the exact samples. Original material.
- video: an 8 s H.264 animatic of the rushed-release scene (steady
  take + poster + six-frame strip) and a per-frame-jittered base take
  showing temporal flicker. No chessboard, pieces, or readable text.
  The flickery clip is larger than the steady one because flicker
  defeats the encoder; that is a teaching beat, not a bug.

No file claims model output. `test_cached_media_availability.py` walks
every fixture, asserts every referenced file exists and serves 200,
and pins the required evidence kinds so the fixtures cannot regress to
metadata-only.

## Timed rehearsal result

Method: the run of show's app interactions were executed in order
against a real backend started fresh with a scratch database and no
provider keys, every step timed (scripted rehearsal on this container;
speech and room time are planned, not measurable here). Measurements:

- Backend boot to healthy, including all seeding: 0.94 s.
- Total presenter system wait across the entire core walkthrough
  (prep chain, six moves plus an illegal attempt, both eval jobs,
  freeze, refusal beat, comparison fetch, exports, all ten media
  fetches): **1.22 s summed**. No single step exceeded 69 ms except
  nothing; the slowest was the 10-file media fetch at 68.8 ms total.
- Skipped in the timed pass: live model turns (no key; the fallback
  path was separately exercised in phase 33's suite), the deck and
  notebook (separate processes; deck builds in 3.6 s, JupyterLab cold
  start is the segment-8 prep item), and actual speech.
- Where the presenter waits for the system: effectively nowhere on the
  core path. The 72-minute core is speech- and participation-bound.
- Full-room check: 40 concurrent simulated attendee browsers each
  fetching adaptation state, artifacts, and evals completed in 2.68 s
  wall (p50 2.39 s for the 3-request bundle) with zero provider calls
  possible (no keys in the environment, and the frontend never talks
  to providers at all: only the backend does, once, when the presenter
  asks).
- E2E: the full Playwright suite including the two new adaptation
  specs (chain-from-the-board, playable-media reveal) passes with
  `CHESS_STUDIO_CHROMIUM=/opt/pw-browsers/chromium` on this machine
  (the container ships a different Chromium revision than the pinned
  Playwright expects; the override is the documented mechanism).

Re-time on the venue laptop after any structural change to
docs/demo-plan.md; the plan's own "Timing evidence" section points
here.

## Cut list (as ordered in the run of show)

1. Segment 5: one game instead of two; skip the scenario beat.
2. Segment 6: skip the live base run and the refusal beat.
3. Segment 7: drop merging, then the ladder animation.
4. Segment 8: walk two notebook cells instead of the arc.
5. Segment 2: compress rules to one slide pass.
6. Segment 4: drop the per-example text inspection (keep all four
   reveals; never cut the regression).

## Standalone Jupyter boundary

Untouched, as required: nothing under `notebooks/` or
`web/public/notebooks/` was read, edited, exported, or regenerated.
The run of show switches to a separately opened JupyterLab
(`just session-notebook`) for segments 8-9 and returns to the board
only when it saves repetition. No notebook panel or iframe exists in
the new UI; the legacy `NotebookShapeUtil` remains untouched for old
snapshots.

## Full-room and offline assumptions

Up to 40 attendees, venue wi-fi that idles out behind a captive
portal. Attendees authenticate to nothing: joining, playing, viewing
panels, and reading state are keyless backend calls. Provider work is
presenter-controlled and single-shot; attendee browsers only read the
stored results, so one generation never becomes forty. Every
workshop-critical artifact is a committed local file served by the
backend; the demo plan's prep checklist verifies each plays before the
room fills. The core path was proven keyless end to end (llm/status
unconfigured, live benchmark 503, everything else 2xx).

## The outcome-first narrative used

Exactly as now written in docs/session-plan.md: (1) compact motivation,
(2) why chess, the minimum rules for non-players, Ramon's route,
Queen's Gambit beat kept, (3) the outcome map and the mantra, (4)
outcome-first reveals of all four modalities from local artifacts, (5)
the shared game building pairs, (6) the adaptation evidence chain with
the freeze, the cached train, the refusal beat, and the
regression-bearing comparison, (7) decomposition, (8) standalone
notebook practice, (9) close from the notebook, never returning to the
deck just to restate it. 72-minute core, 18 flex, advertised 90.
Segments are modular; Ramon can reorder without rebuilding panels or
slides (deck used in two passes over the v1 order; physical slide
reordering deliberately left to phase 35).

## What was built (files)

Backend: `calculations/adaptation.py`, `calculations/comparison.py`,
`compute_explanation_rate` + task-scoped `compute_model_legal_move_rate`
in `calculations/evals.py`, `has_explanation` in
`calculations/llm_prompts.py`, `SFT_PROMPT_VERSION` in
`calculations/export.py`; repos `dataset_snapshots_repo`,
`eval_suites_repo`, `adapters_repo`, `benchmark_runs_repo`,
`list_eval_results_by_run`; `jobs/adaptation_handlers.py`,
`jobs/metric_persistence.py` (shared `persist_metric`); registry gains
`text.train_adapter`, `text.benchmark_eval`,
`{image,audio,video}.adaptation_evidence`; `actions/adaptation.py`
(freeze, seed, state); `routes/adaptation.py` plus the cached-media
route in `routes/artifacts.py`; schema: four new tables, three
`model_attempts` columns, the nullable-workspace rebuild;
`tools/make_media.py` and the `media` extra. Fixtures:
`reference_snapshot`, `eval_suite`, `train_adapter`,
`benchmark_replies`, three `adaptation_evidence` files, three updated
reveal fixtures, eleven media files.

Frontend: `AdaptationPanel` (+ shape util, types, record builder,
canvas migration v5, sync-server schema registration; the committed
snapshot was migrated and settles), `MediaFigure`-based `ArtifactPanel`
with failure states and the raw-payload disclosure, `EvalPanel`
definition/provenance disclosures, `formatDelta`/`shortHash` helpers,
adaptation types and fetchers in `data/api.ts`, evidence jobs in
`modalityJobs.ts`.

Tests: api 370 -> 428, web 234 -> 246, plus two new e2e specs.
Coverage includes snapshot identity and eligibility, suite identity
and multiplicity, registry routing, adapter provenance and the
refusals, checkpoint-tagged attempts, replayed/live provenance,
transport-failure position-set shrinkage, delta refusals end to end,
migration rebuild, cached media availability, and panel states.

## Intentionally deferred

- Phase 35 visual redesign and the general copy pass: the new UI
  follows the current visual language and copy style only.
- Physical deck slide reordering and rewording (phase 35); the run of
  show maps onto the v1 order in two passes.
- The Local/API profile dropdown (phase 35b). This phase records
  resolved model and checkpoint but adds no profile picker.
- The broad architecture refactor (phase 36); new code follows
  actions/calculations/data from the start instead.
- Live training and live adapter serving: out of scope by design, and
  every surface says so rather than hiding it.
- MusicGen-generated audio fixtures: the committed audio is in-repo
  synthesis with exact provenance (the phase allows MusicGen as
  sufficient; it does not require it, and this environment cannot
  download the model). Swapping in MusicGen output pre-workshop is a
  `just make-media`-adjacent change plus a licenses.md update.

## Known issues / tech debt

- `uv run ty check src` reports 5 unresolved-import diagnostics for
  the optional audio extra (`local_audio.py`) in any environment
  without `just install-audio` -- identical on unmodified `main`, not
  introduced here. Installing the extra or adding stub guards would
  clear it.
- `benchmark_runs` accumulates one row per run with no pruning; the
  panel shows all runs for the suite. Fine for a workshop day, worth a
  cleanup action if rehearsals pile up hundreds.
- Older benchmark runs' eval rows are replaced by newer runs with the
  same identity (model/checkpoint/psid), so only the latest runs'
  metrics resolve; superseded runs keep their summary row and
  attempts. The comparison always uses the latest run per checkpoint,
  so this is invisible in the UI, but a history browser would need the
  run journal (attempts + artifacts), not eval_results.
- The adaptation panel polls nothing; it refreshes after its own
  actions. Two presenters driving it from two browsers would need a
  manual reload to see each other's runs.
- `web/e2e/adaptation.spec.ts` uses the `window.chessStudioEditor`
  debug hook to bring the off-grid panel into view; if that hook is
  ever gated to dev builds, keep it available to Playwright.

## What the next phase should tackle first

Phase 35 (deck identity and copy) can start clean. Its first useful
act: reorder the deck to the two-pass mapping the run of show uses
(docs/deck-plan.md documents it) so slide numbers in demo-plan.md
become contiguous ranges, then do the copy pass over the new panel's
labels alongside the rest of the UI. Phase 35b's profile dropdown
should reuse `benchmark_runs.model`/`provider_alias` rather than
inventing a parallel record of what ran where.

## Gotchas

- The training fixture is bound to the reference snapshot BY HASH.
  Regenerating the reference snapshot fixture (or editing
  `PROMPT_TEMPLATE`, which changes every rendered prompt) changes
  hashes and the chain will refuse itself loudly at seed or train
  time. That is the design working; re-derive the dependent fixtures
  together (the authoring path is documented in the fixture notes).
- `model_attempts.workspace_id` NOT NULL relaxation runs as a
  table-rebuild migration inside `init_db`. It commits the pending
  transaction, toggles `PRAGMA foreign_keys` off and on, and must not
  be reordered relative to the ADD COLUMN loop above it. The rebuild
  also makes the table's FK real for legacy synthetic databases; a
  test fixture that inserts attempts must insert the workspace first
  (one pre-existing migration test needed exactly that).
- Benchmark attempts use `task='benchmark_move'`; organic metrics
  filter `task='move'`. Never pool them. If a new metric wants both,
  give it an explicit task parameter like
  `compute_model_legal_move_rate` now has.
- `persist_metric` moved to `jobs/metric_persistence.py` (shared by
  both handler modules). It still writes `modality="text"`
  unconditionally; a non-text computed metric needs that parameterized
  first.
- happy-dom fires `error` on unloadable `<img>` sources by itself, so
  media failure states in component tests assert directly after
  render; firing the event manually finds the img already replaced.
- e2e on this container needs
  `CHESS_STUDIO_CHROMIUM=/opt/pw-browsers/chromium` (revision mismatch
  with the pinned Playwright cache).
- `just make-media` output is byte-stable across runs (fixed seeds, no
  timestamps); if a regeneration diffs, something real changed --
  treat it as a review flag, not noise.
- The e2e suite's shared room accumulates state; the adaptation spec
  tolerates an already-trained adapter (`already_trained` is not an
  error) and never asserts run counts.
