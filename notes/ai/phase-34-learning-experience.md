# Handover: phase 34, complete learning experience

Written 2026-07-20 on branch `claude/p3-learning-experience-gvp2tq`
(the phase's designated working branch in this environment; the comms
README's `phase-34-learning-experience` name refers to the same phase).
Base: accepted `main` at 2b5477a, with phases 32 and 33 merged.

The phase's sentence: the loop "pairs in, adapter out, eval always" is
now observable end to end. Cached training exists and says it is
cached. Invisible training does not exist.

Reviewed 2026-07-20; twelve findings fixed on this branch, then a
second review round landed eleven more, also fixed here. The "Review
corrections" sections below are the delta logs; the rest of this
document has been corrected in place and reads as current truth.

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
   (`sft-v2`, the training template's own version constant; the
   template invites an optional in-JSON `why` field), content
   hash, and the suite's `position_set_id`. Example `ex-12` repeats
   `ex-01`'s position deliberately: multiplicity is data and hashes
   differently. Validation is semantic: every FEN must be a playable
   position (`get_playable_legal_moves` in chess/board.py enforces
   `board.is_valid()`; chess.Board parses a kingless FEN and happily
   generates moves for it), the stored legal-move list is checked
   against the derived one, and the stored prompt against the
   contract's rendered template. Seeding asserts snapshot/suite
   disjointness and is idempotent by content hash.
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
   Live runs gather every reply before any DB write (SQLite's write
   lock is never held across a network wait) and are bounded by a
   per-call timeout, a whole-run deadline
   (`BENCHMARK_RUN_DEADLINE_SECONDS`, 60 s default, clamped 10-300),
   and an abort after three consecutive transport failures; unreached
   examples are recorded as failures with the reason. Metrics are the
   phase 33 calculations plus the new `explanation_rate` (v2: a
   non-empty `why` field inside the reply's JSON), persisted
   insert-only per run via `record_benchmark_metric`: benchmark
   history is immutable, reruns add runs. Each run records the
   `job_config_id` of the job that produced it.
6. **Comparison.** `calculations/comparison.py` emits a signed delta
   with an improved/regressed/unchanged verdict only when suite hash,
   prompt contract, model lineage (base and adapted runs must record
   the same model; a live run of some other configured model is its
   own evidence, never the "before" of a fine-tuning pair), metric
   version, and non-null position-set ids all match. Anything else is
   "not comparable" with the reason, values still visible.
   `GET /adaptation/state` assembles everything the panel renders,
   prefers the latest lineage-matching base run so a cross-model live
   experiment never displaces an honest pair, orders suites
   current-contract-first (`current_contract` flag), and builds the
   comparison for the primary suite only, so an upgraded database's
   stale sft-v1 suite can never present as the benchmark again.

The numbers on the seeded chain: base 7/12 legal (0.58), 10/12 valid
JSON (0.83), 8/12 with a filled `why` field (0.67); adapted 12/12,
12/12, 0/12. Legality +0.42 improved, JSON +0.17 improved,
explanation −0.67 regressed. The regression is contract-compatible by
construction: the sft-v2 prompt invites an optional in-JSON reason,
the scripted base replies fill it eight times, the scripted adapted
replies never do. Say it the way the docs now do: the fixtures are
authored to stage the trade a bare-completion training set makes, and
the chain demonstrates how that trade is measured -- the measurement
is real, the model run is not, and the collapse coexists with a
perfect JSON score instead of contradicting it. It is data, not
styling; the modality evidence fixtures each carry one regression too
(piece identity, clipping, frame detail). Content hashes on the seeded
chain: snapshot `d03be7acc35d1b96`, suite `a274c01d640a346e`, config
`0aa29351f8085e56` (all three moved when the prompt template gained
the `why` invitation; the chain re-derived together, as designed).

## Cached versus live boundaries

- Training: always a cached replay, labelled `cached` on the artifact,
  the adapter row, and the panel, and the panel's banner states the
  whole truth up front: scripted illustration, no model was trained;
  replayed runs replay authored fixtures; only a live base run calls
  a real model. The fixture notes and artifact payloads carry the same
  language.
- Benchmarks: replayed by default (works keyless), badged "replayed
  (scripted)". Live is base-only, presenter-triggered, button exists
  only when `is_llm_configured()` and only for the presenter client;
  the backend independently refuses presenter-only work (live
  benchmarks, image/video/audio generation including local synthesis,
  assessments, non-default opponents; `requests_presenter_generation`
  plus the shared `routes/client_host.py` guard) from any non-loopback
  client with a 403, so the guardrail survives UI bypass. Live and
  replayed runs coexist as separate immutable rows and never blend
  (model+checkpoint are part of eval identity, benchmark metric rows
  are keyed by run, and a live run of a different model refuses
  comparison outright).
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
  core path. The 70-minute core is speech- and participation-bound.
- The review fixes do not change the timed path materially: `run_job`
  now runs the handler before opening the write transaction (the only
  reorder), the loopback guard is an in-process header check, and the
  regenerated fixtures are the same size and shape. The one new wait
  is deliberately bounded: a live benchmark ends at the run deadline
  (60 s default) or the panel's "Stop waiting" button, whichever
  comes first.
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
  Playwright expects; the override is the documented mechanism). The
  final run was executed with a deliberately polluted shell
  (`OPENAI_API_KEY=fake-key-should-be-isolated`): all 11 specs passed,
  proving the test stacks' pinned-empty credentials actually isolate.

Re-time on the venue laptop after any structural change to
docs/demo-plan.md; the plan's own "Timing evidence" section points
here.

## Cut list (as ordered in the run of show)

Deck part 5 (technical reference) is unscheduled by design and is the
first thing that never happens; the optional coda is a rehearsal
decision, not a cut. Within the core:

1. Segment 5: one game instead of two; skip the scenario beat.
2. Segment 6: skip the live base run and the refusal beat; keep
   freeze, train, compare (never cut the regression).
3. Segment 7: walk two notebook cells instead of the arc.
4. Segment 2: three real-world mappings down to one; the A/B slides
   and the reveal table stay.
5. Segment 3: drop the future model tree, then the style beats down
   to Canva alone; the decision slide stays.
6. Segment 1: compress the origin slides to the flight and the meme;
   the TUI recording is never cut.
7. Segment 4: the notation morph alone carries the recap.

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

Exactly as now written in docs/session-plan.md, which follows
deck/PLAN_V2.md as the latest narrative decision: (1) the personal
origin ending in the TUI recording, deliberately before any chess
instruction, (2) four adaptation problems and the A/B "which was
adapted" beat with the regression-bearing reveal table, (3) why adapt
anything, landing on the four-interventions decision (prompt,
retrieve, tools, fine-tune), (4) the delayed chess recap naming
objects the room already watched, (5) the shared game building pairs,
(6) the adaptation evidence chain with the freeze, the scripted
train, the refusal beat, and the regression-bearing comparison, (7)
standalone notebook practice, (8) close from the notebook, with an
optional two-minute whiteboard coda showing what the room produced.
70-minute core, 20 flex, advertised 90; the deck opening (segments
1-4) is 25 minutes, within PLAN_V2's 20-25 target. Segments are
modular; Ramon can reorder without rebuilding panels or slides
(physically rebuilding the deck into PLAN_V2's five-part layout is
phase 35's job; the v1 deck order no longer matches the narrative and
docs/deck-plan.md says so explicitly).

## What was built (files)

Backend: `calculations/adaptation.py`, `calculations/comparison.py`,
`compute_explanation_rate` + task-scoped `compute_model_legal_move_rate`
in `calculations/evals.py`, `has_explanation_field` in
`calculations/llm_prompts.py`, `SFT_PROMPT_VERSION` in
`calculations/export.py`, `requests_presenter_generation` in
`calculations/generation.py`, the shared presenter-machine guard in
`routes/client_host.py`; repos `dataset_snapshots_repo`,
`eval_suites_repo`, `adapters_repo`, `benchmark_runs_repo`,
`list_eval_results_by_run`; `jobs/adaptation_handlers.py`,
`jobs/metric_persistence.py` (shared `persist_metric` plus the
insert-only `record_benchmark_metric`); registry gains
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

Tests: api 370 -> 438, web 234 -> 250, plus two new e2e specs.
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
- The Local/API profile dropdown (phase 35b) and the phase 4b
  named-profile registry. This phase records resolved model and
  checkpoint but adds no profile picker, and every opponent entry
  still shares the one `OPENAI_BASE_URL` and key: per-model endpoints
  (a local Gemma default and a hosted Luna in one picker) exist only
  once the registry integration lands.
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

- `benchmark_runs` and their eval rows accumulate with no pruning
  (immutable history is the point since the review); the panel shows
  all runs for the suite and the comparison uses the latest
  lineage-matching pair. Fine for a workshop day, worth a cleanup
  action if rehearsals pile up hundreds.
- The adaptation panel polls the shared state every 5 s
  (single-flight, `pollMs` prop for tests). That is eventual
  consistency, not sync: two presenters clicking within the same tick
  can still surprise each other, and 40 attendees add a steady 8
  requests/second the load test comfortably covers.
- `web/e2e/adaptation.spec.ts` uses the `window.chessStudioEditor`
  debug hook to bring the off-grid panel into view; if that hook is
  ever gated to dev builds, keep it available to Playwright.
- The presenter-machine guard trusts the LAST `X-Forwarded-For` hop,
  and both dev proxies overwrite the header with the peer address
  they accepted (first-hop trust was spoofable by a client sending
  its own "127.0.0.1" prefix for vite's xfwd to append to). The whole
  scheme still assumes the backend binds localhost so nothing but the
  repo's own proxies can reach it; bind it to a LAN interface and the
  guard must be redesigned, not trusted.
- Stopping a live benchmark from the panel stops the browser's wait,
  not the server run. The duplicate-run guard is server-side since
  round three: `run_job` commits a `run_locks` row before the first
  provider call, refuses a second live run with 409 while it exists,
  and exposes it as `live_benchmark.in_progress` so reloads and other
  tabs restore the locked state. Since round four, startup clears the
  table (a lock that survives its process is orphaned by definition)
  and the 330 s TTL remains only for a process that is alive but
  hung. True server-side cancellation would need the handler to check
  a cancellation flag between gather calls; not built, deliberately.
- Every entry in `OPPONENT_MODELS` resolves against the single
  `OPENAI_BASE_URL` and key. The documented "local Gemma default plus
  Luna in the picker" therefore cannot work across separate llama.cpp
  and OpenAI endpoints yet; that is the phase 4b named-profile
  registry, and this phase treats it as an integration dependency
  rather than claiming it. Until it lands, the room policy fails
  closed on two independent gates: endpoint locality (loopback base
  URL or `OPPONENT_ENDPOINT_IS_LOCAL=1`; budget) and
  `ROOM_MODEL_PLAY=1` set after the real-endpoint load test
  (capacity). The frontier beat is a presenter-machine
  reconfiguration.

## What the next phase should tackle first

Phase 35 (deck identity and copy) can start clean. Its job is the
rebuild to deck/PLAN_V2.md's five-part layout (origin, outcomes,
why-adapt, chess primer, technical reference), with the named
personality beats preserved and the placeholder policy honored:
missing personal assets (the TUI recording above all) stay labelled
placeholders with final geometry, never invented substitutes.
docs/deck-plan.md now marks itself as the v1 build record and lists
the conflicts phase 35 must not inherit (chess-first order, the
invented streak/Elo counter, "moulding intelligence"). Then the copy
pass over the new panel's labels alongside the rest of the UI. Phase
35b's profile dropdown should reuse
`benchmark_runs.model`/`provider_alias` rather than inventing a
parallel record of what ran where.

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
- `run_job` deliberately runs the handler *before* inserting the job
  config, with `job_config_id` generated up front and threaded through
  `JobConfig`. Reordering "config first" reintroduces the held-lock
  bug the review flagged: the config INSERT opens the write
  transaction and a live gather then holds it across network calls.
- Benchmark metric rows are insert-only (`record_benchmark_metric`).
  A test that reruns a benchmark must expect metric rows to
  accumulate (two runs, six rows), not be replaced.
- `PRAGMA defer_foreign_keys` proved non-deterministic in this stack
  (worked in isolated repros, failed inside the real `run_job`
  transaction). That is why `benchmark_runs.job_config_id` is a plain
  TEXT column with a table-rebuild migration dropping the old FK, not
  a deferred constraint. Do not reintroduce the FK.
- `[tool.ty.rules] unused-ignore-comment = "ignore"` exists because
  the optional-extra imports carry `ty: ignore[unresolved-import]`;
  with an extra installed those suppressions would otherwise fail the
  check as unused. All three dependency states (clean, audio, media)
  typecheck; keep it that way when touching optional imports.

## Review corrections (2026-07-20)

Twelve findings from Ramon's review of the initial phase-34 delivery,
all fixed on this branch. What changed and where:

1. **Scripted illustration labeling (high).** The text chain read too
   much like a real adapter run. Now the panel opens with a permanent
   banner ("Scripted illustration: no model was trained. Training and
   replayed benchmarks replay authored fixtures. Only a live base run
   calls a real model."), run badges say "replayed (scripted)", the
   adapter card carries a scripted tag, the comparison labels its
   source, and the fixtures' `notes`/`trainer` fields state the same
   in the artifact payloads. Session plan and demo plan use the same
   language for segment 6.
2. **Write lock across network calls (high).** The live benchmark
   previously ran inside `run_job`'s write transaction. Restructured
   to gather-then-persist: `_gather_live_replies` makes every network
   call with no DB access, then persistence happens in one short
   transaction. `run_job` itself now runs the handler before its
   first insert. Proven by
   `test_live_gather_holds_no_write_lock_during_network_calls`, whose
   fake chat client writes through a second connection during every
   call.
3. **Full-room guardrail enforced server-side (high).** Any attendee
   could previously trigger paid calls through `/jobs`. Now
   `requests_paid_generation` (pure calculation) classifies paid job
   types, and the jobs route 403s them for non-loopback clients
   (X-Forwarded-For first hop, trusted because the backend binds
   localhost behind the repo's own forwarding proxies; both vite
   configs set `xfwd: true`). Client-side, the panel's controls
   render only for the presenter; attendees see the evidence
   read-only with a note.
4. **Explanation regression made contract-compatible (high).** The
   old metric rewarded prose outside the required JSON, so the
   "regression" measured contract-breaking. The prompt contract is
   now `sft-v2`: the template invites an optional in-JSON `why`
   field; completions stay bare moves. `explanation_rate` v2 counts a
   non-empty `why` inside the extracted JSON (`has_explanation_field`
   replacing `has_explanation`). Base replies fill it 8/12; the
   adapter, trained on bare completions, 0/12. The regression now
   coexists with a perfect 12/12 JSON-validity score instead of
   contradicting it. All fixtures regenerated; snapshot hash
   `d03be7acc35d1b96`, suite hash `a274c01d640a346e`, config hash
   `0aa29351f8085e56`.
5. **Immutable benchmark history (high).** Rerunning a benchmark
   previously replaced the prior run's metric rows via
   `persist_metric`'s identity rules. Benchmark metrics now go
   through insert-only `record_benchmark_metric`, keyed by run;
   `test_rerunning_a_benchmark_keeps_both_runs_metric_rows` pins it.
   Organic evals keep the replace-per-identity behavior, which is
   correct for them.
6. **`benchmark_runs.job_config_id` populated (medium).** The run was
   inserted before `run_job` created its config, so the column was
   always null. `run_job` now pre-generates the id, hands it to the
   handler via `JobConfig.job_config_id`, and inserts the config row
   with that id after the handler returns. The column's FK was
   dropped (table-rebuild migration) because it points forward in
   insertion order; consistency comes from the shared transaction.
7. **Bounded live runs (medium).** A live benchmark could previously
   occupy the UI for minutes. Now: 15 s per-call timeout, a whole-run
   deadline (`BENCHMARK_RUN_DEADLINE_SECONDS`, default 60, clamped
   10-300), abort after three consecutive transport failures, and
   unreached examples recorded with the reason. The panel adds a
   "Stop waiting" cancel (AbortController) and a 120 s client-side
   cap.
8. **Semantic suite validation (medium).** `validate_suite_examples`
   previously accepted invalid FEN, garbage move lists, and unrelated
   prompts. It now rejects unknown prompt contracts, illegal FEN
   (python-chess), legal-move lists that differ from the derived
   list, and prompts that do not render exactly from the contract's
   template.
9. **Video frame strip renders (medium).** `frames_url` lived inside
   the fixture's `after` block but the panel only read top-level
   media fields; `MediaFigure` now renders the frame strip, with a
   component test.
10. **Clean-install typecheck (medium).** 18 unresolved-import
    diagnostics across the optional audio imports and the media tool.
    Fixed with `ty: ignore[unresolved-import]` suppressions plus
    `[tool.ty.rules] unused-ignore-comment = "ignore"`. Verified with
    a clean `uv sync` (extras pruned) and with `--extra media`
    installed; the multi-GB audio extra was not installable in this
    container, but `local_audio.py` uses the same suppression pattern
    the media tool does, and the rules config is what makes the
    suppressions safe in both directions.
11. **E2E credential isolation (integration).** The Playwright
    webServer stack and the durability spec's own backend now pin
    `OPENAI_API_KEY`, `VIDEO_PROMPT_API_KEY`, `FAL_KEY`, and
    `OPPONENT_MODELS` to empty strings. The final e2e run was
    executed with a deliberately polluted shell key and passed 11/11.
12. **PLAN_V2 alignment (integration).** docs/session-plan.md and
    docs/demo-plan.md rewritten to deck/PLAN_V2.md's narrative: TUI
    before the chess recap, deck opening 25 minutes (parts 1-4),
    four-interventions framing replacing "moulding intelligence", the
    croissant analogy gone, 5/20/500 with no invented Elo, the
    "rumor/decoration" stage copy removed, scripted-illustration
    language in segment 6, PLAN_V2's whiteboard-failure fallback, and
    the optional coda. docs/deck-plan.md now marks itself as the v1
    build record, defers to PLAN_V2, and lists the conflicts phase 35
    must not inherit. Core timing settled at 70 minutes + 20 flex.

Verification after all fixes: ruff and biome clean, ty clean in every
dependency state, tsc clean, api 438 passed, web 250 passed, deck 10
passed, e2e 11/11 under the polluted-key shell.

## Review corrections, round two (2026-07-20)

Eleven further findings on the corrected build, all fixed on this
branch. What changed and where:

1. **Model lineage in the comparison (high).** A `gpt-5.6-luna` live
   base run received valid deltas against the replayed
   `gemma-4-2b-local` adapter: selection took the latest base run
   regardless of model, and comparability checked only suite and
   prompt identity. `check_run_comparability` now refuses when the
   runs' models differ, and `_build_comparison` prefers the latest
   lineage-matching base run (falling back to the mismatch so the
   refusal renders instead of the comparison vanishing). The old
   end-to-end test had encoded the bug -- it asserted the Luna pair
   was comparable -- and was split into three: matching-lineage
   position-set refusal, the Luna reproduction refusing at run level,
   and a newer Luna run failing to displace an honest pair.
2. **Spoofable forwarding guard (high).** Vite's `xfwd` APPENDS to a
   client-supplied X-Forwarded-For, and the backend trusted the first
   hop, so "127.0.0.1, <lan-ip>" bypassed the 403. Both proxies now
   overwrite the header with the peer address they actually accepted
   (`configure`/`proxyReq`), and the backend
   (`routes/client_host.py`) trusts only the last hop. Either layer
   alone defeats the reproduction; both exist.
3. **Two model calls per exchange per attendee (high).** Every model
   turn auto-fired a scenario assessment, and every black turn calls
   the opponent -- forty attendees on Luna is a burst, forty on
   llama.cpp is a pile-up. The room model policy now exists and is
   enforced: scenario generation is manual (the auto-trigger and its
   refreshKey plumbing are gone) and presenter-machine only (403),
   reviewing stays open to the room; game starts naming a non-default
   opponent are presenter-machine only, so attendees play the room's
   default (configure local Gemma as the default; the frontier beat
   is the presenter's, once, on the projector); the frontend clamps
   attendee picks to the default and hides the picker.
4. **Local MusicGen open to the LAN (high).** Generate controls
   rendered for everyone and local audio was deliberately outside the
   paid-job guard, so attendees could load multi-GB models onto the
   presenter's GPU -- and the route test that asserted local audio
   was "not blocked" actually launched MusicGen on a machine with the
   audio extra, hanging `just test` for seven minutes.
   `requests_paid_generation` became `requests_presenter_generation`
   and covers all generation including local audio; GeneratePanel is
   presenter-only with an honest note for attendees; the test now
   asserts the 403 and can never start a synthesis run anywhere.
5. **Obsolete suite resurfacing (medium).** An upgraded database kept
   its sft-v1 suite, state assembly picked "the first suite with a
   comparison", and the panel picked `suites[0]`, so the old suite
   kept presenting as the benchmark. Suites now order
   current-contract-first (newest first within a contract), carry a
   `current_contract` flag, and the comparison belongs to the primary
   suite or nobody. The panel flags an obsolete primary instead of
   posing.
6. **"Stop waiting" was not cancellation (medium).** Aborting the
   browser request left the server run going, refreshed before it
   landed, and re-enabled the button for a duplicate paid run. The
   panel now tracks the wait: on abort, live controls stay locked
   until a new live run lands through the poll or the server's
   deadline ceiling (300 s clamp plus slack) passes, and the notice
   says exactly that. Server-side cancellation was deliberately not
   built; the deadline bounds the run.
7. **Attendees never saw new evidence (medium).** The panel fetched
   once on mount; tldraw sync carries none of this state. A 5 s
   single-flight poll (test-overridable `pollMs`) keeps every
   attendee's panel current and doubles as the completion signal for
   the live-run lock.
8. **Parseable-but-impossible positions (medium).** Suite validation
   accepted a FEN with no black king because `chess.Board(fen)`
   parses it and generates moves. `get_playable_legal_moves` enforces
   `board.is_valid()`; gameplay keeps the permissive path because its
   positions only ever come from applying legal moves.
9. **Media typecheck under installed NumPy (medium).** `t.max()` in
   the music generator failed ty against the installed NumPy stubs on
   the review machine. Replaced with `float(t[-1])` -- the identical
   value for an increasing arange -- and byte-stability verified by
   regenerating: no diff.
10. **Jobs ran before workspace identity (medium).** `run_job` now
    validates a named workspace with a plain read before invoking the
    runner (no write lock), so a bad id fails in microseconds instead
    of after provider work, and the stale `JobConfig.job_config_id`
    comment describing the pre-fix insert order was rewritten.
11. **Causal training claims in the docs (low).** The plans said the
    adapter "trained on bare completions" stopped explaining, which
    narrates a training run that never happened. Session plan, demo
    plan, architecture, this handover, and the learning guide now
    describe the scripted outcome as what it is: authored replies
    staging the trade bare-completion training would buy, with the
    chain demonstrating how that trade is measured.

Verification after this round: ruff and biome clean, ty clean with
and without the media extra (numpy 2.4.6 installed for the check),
tsc clean, api 448 passed, web 255 passed, deck 10 passed and the
deck builds with the new proxy config, media regeneration
byte-stable.

## Review corrections, round three (2026-07-21)

Four findings on the round-two build, all fixed on this branch.

1. **The room policy trusted configuration (high).** Whatever
   `OPENAI_MODEL` named was treated as attendee-safe, the default is
   Luna on a hosted endpoint, and the policy test itself blessed LAN
   attendees playing it. The policy now fails closed: an attendee
   start of the default opponent requires the endpoint to be known
   local, meaning a loopback `OPENAI_BASE_URL` (derived, zero config
   for the one-laptop room) or an explicit
   `OPPONENT_ENDPOINT_IS_LOCAL=1` for a local endpoint on another LAN
   box (`is_opponent_endpoint_local` in `data/llm_client.py`, gate in
   `routes/game.py`). Localness is never inferred from the model
   name. A misconfigured room now refuses games instead of opening
   forty paid call streams; the presenter machine is exempt because
   its spend is deliberate. The second half of the finding is scoped
   honestly rather than fixed: `OPPONENT_MODELS` only varies the
   model string, every entry resolves against the one base URL and
   key, so the "local default plus Luna in the picker" story is a
   phase 4b named-profile-registry integration dependency, now
   recorded as such here, in the client docstring, and in the demo
   plan's prep step.
2. **Duplicate live runs survived reloads (high).** The round-two
   lock lived in React state; a reload or second presenter tab
   started with `liveWait = null` and could launch the same paid run
   again, and the learning guide claimed otherwise. The in-progress
   identity is now durable and server-side: `run_job` commits a
   `run_locks` row (new table, `data/run_locks_repo.py`, policy in
   `calculations/generation.py:single_flight_lock`) before the live
   gather's first provider call, refuses a concurrent duplicate with
   `JobInProgressError` mapped to 409, releases it in a finally on
   success and failure both, and honors a TTL of the server's own
   deadline ceiling (330 s, matching the panel's `SERVER_RUN_MAX_MS`)
   so a crashed process cannot lock the room out. The primary key is
   the arbiter if two requests race past the read. State assembly
   exposes it as `live_benchmark.in_progress`; the panel derives its
   live-controls lock from `liveWait OR in_progress`, so a reloaded
   panel restores the waiting state from server truth. The lock was
   deliberately not folded into the phase 36 job lifecycle; it is the
   minimal durable identity that makes the refusal enforceable today.
3. **One failed poll blanked the evidence (medium).** `loadFailed`
   replaced the whole panel with "Backend down?" even when shared
   evidence was already on screen. The empty failure state now
   renders only when no state ever loaded; after that, a failed poll
   keeps the last good evidence visible under a stale notice
   ("showing the last loaded evidence; retrying") that clears itself
   on the next successful poll.
4. **"not a before" (low).** The participant-facing comparability
   refusal ended mid-thought. It now reads "its own evidence, not a
   valid baseline for this adapter."

Verification after this round: ruff check and biome clean, ty and tsc
clean, api 454 passed, web 258 passed, deck 10 passed, e2e 11 passed
(Playwright against the real stack). Route-test fixtures now model
the full-room local-endpoint configuration explicitly; the
fail-closed posture has its own test that removes it.

## Review corrections, round four (2026-07-21)

Four findings on the round-three build, all addressed on this branch.

1. **Locality is not capacity (high).** The round-three gate opened
   attendee model play to any local endpoint, and the demo plan sent
   the whole room there: forty simultaneous Gemma requests queue
   behind one llama.cpp server and exhaust the 30 s model-turn
   deadlines even though every call is free, and the prescribed load
   test ran against the mock, which measures the backend but not
   inference. The room now opens on measurement, not location.
   Attendee timed games AND model replies (`/model-move` works on
   free-play boards, so the gate lives on both routes) require the
   locality gate plus `ROOM_MODEL_PLAY=1`
   (`is_room_model_play_open`), and the flag's documented workflow is
   the real load test: backend pointed at the actual llama.cpp
   endpoint on the venue laptop, `just load-test 40` (the sim already
   drives `/model-move` and reports per-endpoint percentiles from
   loopback, which passes the presenter gates), model-move p95 inside
   `MODEL_TURN_DEADLINE_SECONDS` with zero errors, numbers recorded.
   The explicit room workflow for the default (closed) posture is in
   the demo plan's segment 5: attendees free-play (same dataset rows,
   same rewards, same replace-in-place beat), model inference happens
   once, presenter-led, on the projector; attendee panels render
   "Free play today" instead of a Start button that would 403
   (`room_model_play` on `/llm/status`). The venue measurement itself
   is prep work only Ramon can run; the repo's part is that nothing
   opens without it.
2. **A restart preserved a false lock (medium).** The 330 s TTL was
   doing double duty. A crashed backend cannot carry an in-flight run
   across a restart, so startup now clears `run_locks`
   (`main.lifespan`), and the TTL covers only what startup cannot
   see: a process that is alive but hung. Tested with two TestClient
   lifecycles over one database.
3. **The race tested as a race (low).** The pre-inserted-lock test
   stands, but two new tests prove the guarantee itself: one holds a
   runner mid-flight on one connection while a second connection is
   refused before its runner starts (threading.Event as the
   barrier), and one pins the read-race interleaving by forcing both
   acquires to read an empty table, so the primary key's arbitration
   is exercised deterministically rather than assumed.
4. **Guide tone (low).** The round-three learning-guide section
   stacked metaphors; it now states its points directly with one
   aside kept, and the round-four section follows the same rule.

Verification after this round: ruff check and biome clean, ty and tsc
clean, api 458 passed, web 260 passed, deck 10 passed, e2e 11 passed
(Playwright against the real stack; its backend pins empty
credentials, so the panels take the unconfigured-LLM path and the new
gates never fire from loopback anyway). The venue-laptop load test
against real Gemma remains open prep work by design: the repo cannot
run it, and nothing opens the room until someone does.
