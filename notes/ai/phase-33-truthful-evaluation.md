# Handover: phase 33, truthful evaluation and data

Written 2026-07-20 on branch `phase-33-truthful-evaluation`. The four
honesty breaks from the review are closed: valid_json_rate measured the
app's own json.dumps, legal-move metrics mixed participant and model
moves, dataset targets lied about what they were, and scenario
assessments lived in React state while an illegal model reply could
strand the board on black's turn.

## The Chat Completions contract

One transport, `data/llm_client.py`, for every text-model call. It only
ever calls `{base_url}/chat/completions` (trailing slashes stripped),
sends `messages` plus a configurable model, validates
`choices[0].message.content` before indexing, and returns a
`ChatOutcome`: content, model, provider alias, attempt count, request
ids, and capability-fallback flags. Callers persist provenance from
that object instead of re-deriving it. No Responses API call exists,
and `api/tests/test_model_reference_guard.py` fails the suite if one
appears or if `gpt-5.5` in any spelling returns to active sources
(notes/ handovers are historical records and deliberately unscanned).

Two typed profiles: `opponent` (`OPENAI_*`) and `video_prompt`
(`VIDEO_PROMPT_*`, each field falling back to its `OPENAI_*`
counterpart). A boundary test proves local Gemma opponent play and
hosted Luna scene writing coexist in one process with no endpoint,
model, or capability leakage.

Capabilities live in `calculations/model_catalog.py`, not string
checks: `gpt-5.6-luna` gets `reasoning_effort: medium`; both Gemma
spellings (`gemma-4-2b-local`, the GGUF repo id) do not, because
llama.cpp rejects it; unknown models get the conservative profile (no
reasoning_effort, JSON mode allowed).

Capability fallbacks are narrow and provenance-visible: a 400 whose
error message names `response_format`/`json_object` or
`reasoning_effort` drops exactly that field once and retries. Any
other 400 fails loudly with a bounded excerpt. `json_mode_dropped` and
`reasoning_effort_dropped` ride on the outcome and the attempt record.

Retry policy: 429/5xx/transport failures retry with exponential
backoff, jitter, and `Retry-After` (capped at 30s), two retries max.
Timeout is capped at 120s; move calls use a documented 60s because the
game clock keeps running. Every failing `x-request-id` is retained on
the raised `LlmRequestError` (as `request_ids`), and diagnostics never
contain the API key or the prompt (a test asserts both).

### The transient 401 exception, now evidence-based

The exact generic message "You have insufficient permissions for this
operation" may retry at most twice, and only with evidence the
credential is real: the same (base_url, key) fingerprint already got a
200 in this process, or the operator set `OPENAI_RECENT_KEY_401_RETRY=1`
after creating or rotating a key. Without evidence, even the generic
message fails immediately. Invalid-key, revoked, IP-policy, and
project/model-denial responses never retry. This is stricter than the
previous behavior (which retried the generic message unconditionally);
the phase prompt required the recent-key case to be an explicit opt-in
rather than guessed from the response.

## Schema changes (migration in db.py, in place, preserves data)

- `moves` gains `actor` (participant | model | fallback | unknown) and
  `model`. Pre-existing rows get `unknown`, not a guess: white/black
  inference is not airtight because a participant can move black
  pieces in free play. Unknown rows are excluded from per-actor
  metrics.
- `model_attempts` (new, immutable): one row per raw model reply or
  transport failure. Columns cover task (move | scenario), actor,
  model, provider_alias, prompt_version, checkpoint (for phase 34),
  ply, fen, attempt_number, status, raw_response, request_ids_json,
  json_requested, parse_ok, parsed_move, is_legal, applied_move_id,
  error_detail.
- `scenario_assessments` (new): suggested_* written once, final_*
  written by review, status suggested | accepted | edited | failed,
  plus model/provider_alias/prompt_version and an attempt_id link.
- `eval_results` gains numerator, denominator, unit, direction,
  definition, version, scope_json, note. Cached fixture notes finally
  survive seeding (they were dropped before; the table had no column).

Prompt versions are constants in `llm_prompts.py` (`move-v1`,
`assess-v1`). Bump them when prompt text changes meaningfully.

## Transaction boundaries

Repositories on the game path (moves, dataset_rows, games, workspaces,
eval_results, model_attempts, scenario_assessments) no longer commit;
actions do. `make_move` commits move + board + dataset rows + game
outcome atomically and rolls back on failure (tested from a second
connection). The model turn commits failed attempts individually as
they happen (evidence must survive a failed turn, also tested via a
second connection) and commits the applied move with its attempt
record in one transaction. `expire_if_over` commits its timeout loss
on its own: the flag fell regardless of what the surrounding action
was doing. `start_over` commits the resignation loss and the fresh
game together. `reset_page` clears scenarios, attempts, dataset rows,
moves, and games leaf-to-root in one transaction. `run_job` persists
config + artifact + eval rows together. Single-write paths (users,
pages, presenter_state, job_configs, artifacts) keep their repo-level
commits; nothing composes them.

## The model-turn state machine

`actions/model_turn.py`. Per attempt: transport_failed | empty |
parse_failed | invalid_move_syntax | illegal | applied. Limit from
`MODEL_TURN_MAX_ATTEMPTS` (default 2, clamped 1-5). Terminal outcomes:

- Model answered garbage at least once: deterministic fallback, the
  first legal move in UCI sort order, applied under actor `fallback`
  with an attempt row noting why. The game continues; garbage can
  never count as model skill because metrics filter by actor.
- Every attempt died in transport: outcome `unavailable`, nothing
  moves, the response says so factually, and the workspace shows a
  Retry model move button. Loud waiting, not silent sticking.

The route returns the outcome, the attempts, and a detail sentence.
The old behavior (illegal model reply inserted into `moves` with
reward -1) is gone; deck and demo plan were updated accordingly.

## Metric definitions (calculations/evals.py, all typed MetricResult)

- `legal_move_rate` v2: legal moves / recorded move attempts by one
  actor (default participant), from `moves`.
- `model_legal_move_rate` v1: attempts whose reply parsed to a legal
  move / model replies received, from `model_attempts` (task=move,
  actor=model, raw_response present). Transport failures excluded from
  the denominator; retries all count; fallback excluded. Filterable by
  model, game, checkpoint: that is the before/after contract for
  phase 34 (same frozen input set, both versions identified in scope).
- `valid_json_rate` v2: raw replies parsing as a JSON object / replies
  received where JSON was requested, parsed with the same
  `extract_json_object` the app uses to consume replies.

Empty samples return `available: False` and are not persisted; the job
payload reports them explicitly. Example real run (mock LLM, 2
participant moves, 2 illegal-JSON replies, 2 prose replies):
legal_move_rate 1.0 (2/2, actor=participant), model_legal_move_rate
0.0 (0/4, actor=model), valid_json_rate 0.5 (2/4, task=move).

## Dataset honesty

- `board_tensor_to_move_class` stores a real class index from
  `calculations/move_vocab.py` (`from*320 + to*5 + promo`, size 20480,
  invertible, tested against every legal opening move and promotions)
  plus `target_uci`. The deck's example is now 3980 = e2e4.
- `policy_value_to_move` became `policy_move_reward`: one-hot policy on
  the move played, `move_reward` named for what it is, with a note
  stating it is not a position value and what a real one would need.
  Rows are complete at move time; unfinished games need no backfill.
- `docs/datasets.md` is the new contract file: input, target, type,
  when known, and objective for all six shapes plus scenario exports.
  Old DB rows keep their old shape string and render under a labelled
  legacy entry in the dataset panel.

## Scenario persistence

`actions/scenario.py` + `data/scenario_repo.py`. Suggest persists the
raw reply (via model_attempts) whether or not it parses, then the
scenario row. Review (accept/edit) writes final_* without touching
suggested_*. Failures insert an explicit failed row; prior records are
never erased; reload (`GET /workspaces/{id}/scenario`) returns the
latest non-failed row. `POST /datasets/scenarios/export` writes
`chess_scenarios.jsonl` with `suggested` and `approved` separated so
presenter exports distinguish raw model output from vetted examples.
The frontend `ScenarioSection` is a focused component that renders
API state; persistence orchestration left `WorkspacePanel`.

## Compatibility concerns

- Existing databases migrate in place; nothing is dropped. Old moves
  are actor `unknown` and excluded from per-actor metrics, so a
  pre-phase database shows unavailable model metrics until new turns
  happen. That is correct, if surprising on first look.
- The old `/model-move` response shape changed (MoveResponse ->
  ModelTurnOut). The web client in this repo is the only consumer and
  was updated with it.
- `assess` now returns the persisted ScenarioOut instead of the bare
  three fields; same single-consumer situation.
- The generic-401 retry is stricter than before (evidence required).
  If the workshop key is rotated the morning of, set
  `OPENAI_RECENT_KEY_401_RETRY=1` in the env.
- The mock LLM's default behavior is unchanged; the new `--move-mode`
  flags are opt-in, so `just load-test` rehearsals behave as before.

## Tests run

- `just lint` (ruff + biome): clean.
- `just typecheck` (ty + tsc): clean.
- `just test`: api 320 passed, web 210 passed, deck 10 passed.
- `just test-e2e`: 9 passed (room 4, smoke 4, durability 1).
- Manual failure-path run against a real backend + mock LLM:
  illegal mode -> fallback a7a5 with two persisted illegal attempts;
  invalid (prose) mode -> fallback with two parse_failed attempts;
  mock killed -> outcome unavailable in ~6.5s with two
  transport_failed attempts and an unchanged board; prompt_eval over
  that evidence produced the example metrics above; scenario
  suggest -> accept -> reload -> export round-tripped with provenance.

## Post-review corrections

Ramon's review of this branch found nine real defects, all now fixed
on top of the work above (separate commits, same branch). Each was
reproduced before being fixed.

1. **Concurrent model turns could misapply stale replies.**
   `model_turn` snapshotted fen/legal_moves before the network call but
   applied the reply to whatever board existed later with no
   precondition, and never checked `make_move`'s actual result --
   trusting the stale snapshot instead. Reproduced: two overlapping
   replies for the same position, second one's attempt record claiming
   `status=applied, is_legal=1` for a move that was actually illegal on
   the board it landed on. Fixed with `MovePrecondition` (fen, game_id,
   ply): a mismatch raises `StaleMoveError` before anything is written;
   the attempt is recorded `status=stale` instead of guessed, and the
   turn returns a new `stale` outcome. The applied-branch attempt
   record now also reads `move_result.move["is_legal"]` instead of
   hardcoding `True`.
2. **Empty eval runs left stale results on display.** An unavailable
   metric skipped persisting rather than clearing the prior scoped row,
   and `reset_page` never touched `eval_results`. Reproduced: a 1/1
   result surviving both a page reset and a subsequent empty
   re-run. Fixed: an unavailable metric now deletes its prior scoped
   row (`delete_eval_result`), and `reset_page` clears computed
   `eval_results` for the workspaces it wipes.
3. **The promised phase-34 contract didn't actually exist.**
   `replace_eval_result`'s identity ignored `scope_json`, so a
   differently-scoped rerun (a different model) silently clobbered the
   prior one, and the job never threaded model/checkpoint params
   through at all. `eval_results` gained real `model`, `checkpoint`,
   `run_id`, and `sample_ids_json` columns; identity is now
   `(modality, metric, workspace, source, model, checkpoint)`, so a
   base and an adapted model's results coexist; `text_prompt_eval`
   accepts `model`/`checkpoint` job params and threads them into the
   metrics. `sample_ids` records the exact row ids a value was computed
   from -- the frozen input set, auditable after the fact.
4. **Exports weren't self-contained or provenance-safe.** The
   `board_tensor_to_move_class` row's own note claimed the tensor was
   "cheap to regenerate from the FEN" while storing no FEN; fixed by
   adding it. The full archive dropped `move_id` and any join to the
   producing move; it now joins `dataset_rows` to `moves` (LEFT JOIN,
   since `move_id` is nullable) and includes `move_id`, `game_id`,
   `actor`, `model`. That join surfaced a real data-quality bug: a
   fallback move's arbitrary lexicographic pick was indistinguishable
   from a real answer in `chess_sft.jsonl`. `calculations/export.py`
   now defines `is_training_eligible` (participant and model only) and
   the SFT export filters on it; the full archive keeps every row but
   tags each with an explicit `training_eligible` boolean.
5. **Capability-fallback provenance was computed and discarded.**
   `ChatOutcome.attempts`/`json_mode_dropped`/`reasoning_effort_dropped`
   were never written anywhere. `model_attempts` gained matching
   columns; both `model_turn.py` and `scenario.py`'s shared per-reply
   dicts now include all three.
6. **`run_job` wasn't actually atomic.** `job_configs_repo` and
   `artifacts_repo` each called `conn.commit()` internally despite
   `run_job`'s own comment claiming one transaction, which flushed a
   handler's `eval_results` writes prematurely. Reproduced: a forced
   artifact failure left one committed config, no artifact. Both repos
   no longer commit; `run_job` wraps its three writes in the same
   try/rollback/raise pattern as `make_move`.
7. **Turn ownership was UI-only.** The public move route always
   recorded the caller as `actor=participant` with no server check.
   Reproduced: after participant e2e4, participant e7e5 (black's move)
   was accepted. `make_move` now raises `NotYourTurnError` (409) for a
   participant move on the wrong turn in an active game; free play is
   unrestricted; model/fallback moves are exempt. The frontend also
   gates `boardInteractive` on whose turn it actually is, not just
   locked/pending/thinking.
8. **Timeout handling could overrun the game and lose evidence.**
   Attempt-count-only bounding let worst-case latency reach roughly six
   minutes (transport retries times model-turn retries), and a
   legitimate reply arriving after clock expiry vanished with zero
   persisted attempts (`make_move`'s clock check raised before
   `model_turn` recorded anything). Fixed with one overall
   `MODEL_TURN_DEADLINE_SECONDS` (default 30s) checked before each
   attempt, the last attempt's timeout capped to the remaining budget,
   and a new `clock_expired` attempt status recorded before
   `GameClockExpiredError` re-raises.
9. **Failed scenarios vanished on reload; review failures were
   silent.** `latest_scenario` explicitly excluded `status='failed'`
   rows, so reload after a failed assessment silently showed the
   pristine empty state. It now returns the true latest row regardless
   of status, and `ScenarioOut` exposes `error_detail` so the frontend
   renders the same recoverable error state a live failure shows.
   Separately, `accept()` swallowed review failures
   (`.catch(() => scenario)`) and `saveEdit()` set an error without
   setting the state that gates rendering it; both now surface the
   failure, with an `errorSource` distinguishing an assessment failure
   from a review failure so the retry button's label stays honest.

Every fix above has a dedicated reproduction test at the layer where
the bug lived (repository, action, route, or component), plus the full
suite, lint, and typecheck rerun clean after each one. Final counts:
api 349, web 216, deck 10.

## Round 2 corrections

A second review pass found seven more defects, three of them in fixes
from the round above. Same discipline: reproduce first, fix minimally,
rerun the full suite plus lint and typecheck after each one, separate
commits on this branch.

1. **The move precondition was still check-then-write.** Round 1 added
   `MovePrecondition`, but `make_move` read workspace/game state and
   checked it *before* the first write, leaving a real gap for another
   connection to write in between. Reproduced with two genuine
   `sqlite3.connect` connections synchronized on a `threading.Barrier`
   racing the same legal move against the same precondition (a
   same-connection nested call doesn't exercise this window at all,
   since SQLite serializes writes on one connection by construction).
   Fixed with `conn.execute("BEGIN IMMEDIATE")` acquired *before*
   rereading workspace/game/ply, so the write lock is held for every
   state-dependent decision, not just the final INSERT; the two-
   connection barrier test now asserts exactly one success and one
   `StaleMoveError`, with exactly one legal-move row in the database.
2. **The eval contract still had no real frozen input set, plus a
   checkpoint bug.** `sample_ids_json` recorded output row ids, which
   are not comparable across models -- two models never produce the
   same ids even over identical positions, so "same sample_ids" can
   never be a proof of comparability. Separately, `valid_json_rate`
   never filtered by checkpoint at all, so with one model and two
   checkpoints in play, a single unscoped row silently pooled attempts
   from both. Fixed: `compute_position_set_id` hashes the sorted,
   deduplicated FEN strings a metric actually ran over (order- and
   duplicate-independent), giving two runs a way to *prove* they
   measured the same positions instead of the reader having to trust
   matching scope. `MetricResult` gained a `positions` field alongside
   `sample_ids`; `eval_results` gained `position_set_id`/
   `position_set_json`. Storage identity split in two:
   `_scope_clause` (used by `delete_eval_result`, clears every window
   for a scope when a metric goes unavailable) versus
   `_scoped_identity_clause` (used by `replace_eval_result`, includes
   `position_set_id` so two different position-set "windows" for the
   same model/checkpoint coexist instead of overwriting each other).
   `compute_valid_json_rate` gained the missing `checkpoint` param.
3. **The overall model deadline wasn't actually a deadline.**
   `model_turn` computed its remaining budget correctly, but passed it
   to `llm_client.chat` as a per-attempt timeout that `_chat_completion`
   then handed unchanged to up to three internal HTTP attempts plus
   uncounted backoff sleeps between them -- a 0.2s deadline could take
   0.668s, a 30s default could approach 90s plus backoff. Fixed by
   having `_chat_completion` turn its `timeout` argument into one
   absolute deadline at the start of the call, then recomputing the
   time left before every attempt (passed as that attempt's real
   `client.post(..., timeout=remaining)`) and before every backoff
   sleep (`_sleep_backoff` caps the sleep to whatever remains, so a
   sleep can no longer itself blow the budget). A fake-monotonic-clock
   test proves the total elapsed time for a scripted failure sequence
   stops exactly at the declared deadline instead of running the full
   retry ladder regardless.
4. **Turn ownership and stale recovery were still incomplete.** Two
   separate gaps under one finding: `make_move`'s turn check (round 1)
   only ever rejected the participant for playing the model's color --
   nothing checked the symmetric case, so a raw `/model-move` call
   right after `game/start` let the model immediately play White's
   opening move. Fixed with a mirrored check in the same write-locked
   section (`actor in ("model", "fallback")` rejected when the fen
   shows the participant's color to move), plus an earlier bail at the
   top of `model_turn` itself so a wrong-turn call never even spends an
   LLM request. Separately, `WorkspacePanel`'s `refreshGameStatus` --
   the resync path for a stale reply, a 409 clock expiry, or a turn
   race -- called `applyGameStatus` without `{ board: true }`, so the
   local fen never actually updated on any of those resyncs even though
   game/record/history did; a stale board could then retrigger the
   model on a turn the server had already moved past. One-line fix:
   pass `{ board: true }`. Two existing model_turn tests had a latent
   setup bug this exposed (`start_game` then `model_turn` with no
   participant move first was itself the round-1 bug, not a valid test
   of clock-expiry timing); both now play a move first.
5. **`policy_move_reward` still wasn't self-contained.** Round 1 fixed
   `board_tensor_to_move_class`'s missing fen; `policy_move_reward` had
   the same gap -- only `policy_target` (legal-move keys) and
   `move_reward`, no fen, and a legal-move set is not the position (the
   same set of legal moves can arise from more than one arrangement of
   pieces). Fixed by adding `"fen": move.fen_before` to the payload,
   same field and source as every other shape. Updated the shape's
   contract in `docs/datasets.md` and the deck's illustrative slide.
6. **Terminal transport failures still lost capability provenance.**
   Round 1 fixed this for the success path (`ChatOutcome`); a call that
   dropped JSON mode on an early attempt and then still exhausted its
   retries for an unrelated reason raised `LlmRequestError`, which only
   ever carried `status_code`/`request_ids` -- the stored failed
   attempt recorded a null transport count and null fallback flags, as
   if no capability had ever been dropped. Fixed by extending
   `LlmRequestError` with the same three fields `ChatOutcome` carries,
   threading them through every raise site in `_chat_completion`,
   `_request_error`, and `_extract_content` (the malformed-200-body
   paths can also follow a capability fallback), and reading them off
   the caught exception in both `model_turn.py` and `scenario.py`.
7. **Reload still lost the previous mapping after a later failure.**
   Round 1 made a failed scenario visible on reload (`latest_scenario`
   returns the true newest row); it did not handle a failure landing
   *after* a success. A live failure never erases the on-screen mapping
   (the component only calls `setScenario` on success), but the reload
   endpoint returned only the single latest row, so a later failure
   made an earlier good suggestion unreachable the moment the page
   refreshed -- the client got the failure and nothing else. Fixed by
   returning two rows: `latest` (unchanged) and the new
   `latest_success` (`latest_successful_scenario` in the repo, the most
   recent non-failed row). The frontend restores `latest_success` into
   the displayed mapping and, only when `latest` is itself a failure,
   additionally shows the same error-with-retry state a live failure
   renders -- reconstructing the live-failure combination instead of
   only ever showing whichever row is newest.

Final counts after round 2: api 368, web 217, deck 10.

## Round 3 corrections

A third review pass, run after independently re-verifying all of round 2 (368
api, 217 web, 10 deck, lint, both type checkers, Playwright 9/9 all passed
clean on their own before this round's six findings were raised). Same
discipline as the rounds above: reproduce, fix minimally, rerun the full
suite plus lint and typecheck after each one, separate commits.

1. **The eval panel showed every historical run, not just the current
   one.** `eval_results` correctly keeps every position-set window a
   re-run produces (round 2's fix), but the panel rendered every row
   with no model/checkpoint/time label -- three runs over a growing
   move history became six indistinguishable rows with denominators 1,
   2, and 3. Fixed with a pure frontend reduction, not a backend data
   change: `calculations/evalResults.ts`'s `latestEvalResultsByScope`
   keeps only the newest row per (modality, metric, source, workspace,
   model, checkpoint) before `EvalPanel` renders; rows that still
   coexist after that (a base checkpoint next to an adapted one) get a
   small model/checkpoint label plus a provenance tooltip so they read
   as distinct measurements, not duplicates.
2. **A move could cross the game deadline while blocked on the write
   lock.** `make_move` checked clock expiry before `BEGIN IMMEDIATE`.
   The reviewer held the writer lock (a second real connection) until a
   backdated ~0.2s-remaining game genuinely expired, and the blocked
   move was accepted afterward with the game still active -- the same
   check-before-lock shape as the round-2 precondition bug, just for
   the clock instead of the board state. Fixed by moving the check
   inside the write lock, on a fresh `get_active_game` read taken after
   `BEGIN IMMEDIATE` returns. The original worry about nesting
   `expire_if_over`'s own commit inside this transaction turned out not
   to apply: on the expired branch this call's very next action is to
   raise, so there is nothing later in the transaction for an early
   commit to leave half-done.
3. **A model turn-ownership 409 displayed a false timeout loss.**
   `/model-move` maps both `GameClockExpiredError` and
   `NotYourTurnError` to 409; `triggerModelReply()` treated every 409
   as a clock expiry. A late duplicate model-move request losing a
   turn-ownership race (the turn changed while it was in flight) would
   show "Time ran out. That is a loss." even though the game was still
   running. `handleMove` already distinguished this on the
   participant's move path (checking the 409 detail for "model's
   turn"); `triggerModelReply` got the mirrored check for "participant's
   turn" instead of routing every 409 to `handleClockExpired()`.
4. **`position_set_id` deduped positions, hiding repeat-sample
   denominators.** The hash removed duplicate FENs before hashing, so a
   sample with three distinct positions once each and a sample with one
   position sampled a hundred times could get the identical id, despite
   representing wildly different measurements. Fixed by hashing the
   sorted list with duplicates intact -- still order-independent,
   deliberately no longer duplicate-independent, since every repeated
   attempt is a real row in the denominator.
5. **The deadline-exceeded bail-out overcounted transport attempts.**
   `_chat_completion` incremented `attempt` at the top of the retry
   loop before checking whether the deadline had already expired, so a
   bail-out (no request made) still counted as an attempt. One real
   HTTP call followed by a deadline bail-out was reported as two
   transport attempts. Fixed by moving the increment to just before the
   real `client.post`, after the deadline check.
6. **The README was behind phase 32.** It still described canvas
   persistence as a whole-shared-snapshot overwrite, presenter
   navigation with no exact camera target, and a hardcoded
   `/opt/pw-browsers/chromium` Chromium path -- all three fixed in
   phase 32 (real multiplayer sync with per-record conflict resolution,
   camera-bounds-first presenter targeting, Playwright's own default
   browser discovery with an optional env override).
   `docs/local-dev.md` already had this right; only `README.md` had
   drifted.

Final counts after round 3: api 370, web 226, deck 10.

## Intentionally deferred

- The visible adaptation loop (before/after comparison UI) is phase
  34; this phase ships the backend contract (checkpoint column, scoped
  metrics, frozen-set filtering).
- Broad frontend component extraction stays in phase 36;
  ScenarioSection was the one focused extraction this phase needed.
- Deck visual redesign and the general copy pass are phase 35; only
  technically false statements were touched.
- No live provider request was made; the checked-in cached scenario
  fixtures remain labelled illustrative.

## Known issues / tech debt

- `text_reward_eval` still sums rewards over all actors' moves. It is
  a sum, not a rate, so nothing is mislabelled, but a per-actor split
  would be more useful teaching material.
- The eval panel now shows model/checkpoint as a small label plus a
  provenance tooltip (definition, model, checkpoint, run timestamp);
  a fuller popover rendering the raw `scope_json` is still not built.
- `model_attempts.checkpoint` is always NULL until phase 34 writes it.
- The legacy `policy_value_to_move` label mapping in DatasetPanel can
  go once rehearsal databases are reset for the workshop.
- sqlite3's implicit-transaction behavior means a future repo function
  that forgets the no-commit rule reintroduces partial writes
  silently. The atomicity tests catch the move path; new composed
  actions should copy that second-connection test pattern.

## What the next phase should tackle first

Phase 34 (learning experience) should build the visible adaptation
loop directly on `model_legal_move_rate` scoped by model/checkpoint:
run a frozen set of positions through two models or checkpoints and
show both MetricResults side by side. See "Post-review corrections"
and "Round 2 corrections" above for the schema and job-handler work
already done to support this (an earlier draft of this handover
wrongly claimed no schema work was needed; `eval_results` gained real
identity columns, and then `position_set_id`, for exactly this
reason). `compute_position_set_id` is the piece that actually proves
two runs measured the same positions -- worth reading before building
a benchmark runner on top of it, so the runner produces sets that
hash-match on purpose rather than by accident.

## Gotchas

- Run api commands from `api/` (`uv run pytest` at repo root picks up
  the notebook venv on Python 3.14 and collects nothing useful).
- `expire_if_over` commits. If you compose it inside a larger
  transaction, your uncommitted writes get committed with it. Call it
  before starting composed writes, as `make_move` does.
- `ChatOutcome` is frozen; tests that stub `llm_client.chat` must
  return one (see `fake_outcome` helpers in the action tests).
- The WorkspacePanel model-reply effect fires on fen changes only. An
  `unavailable` turn leaves fen unchanged by design, so the retry
  button is the only thing that re-triggers it. Do not "fix" that by
  adding modelThinking to the dependency list; it retries forever.
- `make_move`'s `BEGIN IMMEDIATE` will raise "cannot start a
  transaction within a transaction" if a test helper leaves an
  uncommitted implicit transaction open before calling it (e.g.
  `insert_user` + `insert_workspace` with no `conn.commit()` between
  them and the call). Not a production issue -- route-level connections
  are always fresh per request -- but every `make_workspace` test
  fixture needs that commit now.
- Testing anything deadline-shaped against real wall-clock time is
  slow and flaky. `test_llm_client.py`'s deadline tests redirect both
  `time.monotonic` and `time.sleep` to a small `_FakeClock` (`sleep`
  advances the same counter `monotonic` reads), which makes multi-
  attempt-plus-backoff timing assertions exact and instant instead of
  approximate and slow. Reach for that pattern before reaching for
  `pytest.approx` and a real `time.sleep`.
- When a fix changes behavior that an existing test's *setup* was
  accidentally relying on (not just its assertions), the test will
  fail somewhere confusing. The turn-ownership fix broke two
  clock-expiry tests whose setup was `start_game` then `model_turn`
  with no participant move in between -- which was the round-1 bug
  being exercised as if it were valid, not a real clock-expiry
  scenario. Read what a failing test's setup actually establishes
  before assuming the fix is wrong.
- pkill in this sandbox kills the calling shell's process group too;
  use targeted `kill $(pgrep -f ...)` when scripting rehearsals.
- To test that a blocked writer sees genuinely fresh state once its
  `BEGIN IMMEDIATE` finally returns (the clock-expiry-during-lock-wait
  fix), synchronize with a `threading.Event` the holder sets right
  after it acquires the lock, not a `threading.Barrier` both sides
  wait on. A barrier only guarantees both threads *start* around the
  same time; it does not guarantee which one wins the race for the
  lock, and this test needs the holder to provably have the lock
  before the move attempt even begins.
- A retry-loop attempt counter must only increment right before the
  request it is counting for actually fires. Incrementing earlier (at
  the top of the loop, before a deadline or other precondition check
  that might bail out first) counts attempts that never reached the
  network -- exactly the shape of the round-3 overcounting bug in
  `_chat_completion`.
