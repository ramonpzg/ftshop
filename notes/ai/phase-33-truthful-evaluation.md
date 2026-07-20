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
- The eval panel shows scope only via tooltip/counts; a fuller
  provenance popover could render scope_json.
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
below for the schema and job-handler work already done to support
this (an earlier draft of this handover wrongly claimed no schema work
was needed; `eval_results` gained real identity columns for exactly
this reason).

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
- pkill in this sandbox kills the calling shell's process group too;
  use targeted `kill $(pgrep -f ...)` when scripting rehearsals.
