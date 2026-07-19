# Phase 2 prompt: truthful evaluation and data

Use this prompt only after phase 32 has been reviewed and accepted.

## Prompt

You are implementing phase 33 of `euro-scipy-chess-studio`: make the text
workshop's data, model attempts, scenario mapping, rewards, and evaluations
technically honest.

The workshop teaches that participants can inspect the complete path from game
behavior to training rows and evaluation. The current implementation breaks
that contract in four places:

1. `valid_json_rate` parses JSON produced by the application's own
   `json.dumps`, not raw model replies.
2. Legal-move metrics mix participant moves and opponent-model moves because
   the durable move record has no actor or model provenance.
3. `target_move_class` is a UCI string while the deck presents an integer
   class. The so-called position value is an immediate shaped move reward, and
   rewarding every legal move can encourage games to continue rather than end
   well.
4. Real-world scenario assessments are ephemeral React state, and an illegal
   model reply can leave the game stuck on black's turn.

The goal is not sophisticated chess research. The goal is a small system whose
stored evidence and visible labels agree.

There is also a corrected model-call direction that this phase must preserve
and harden. OpenAI-compatible calls use `/chat/completions`, not the Responses
API. `gpt-5.5-mini` does not exist. Ramon has supplied a working Chat
Completions implementation using the configurable default `gpt-5.6-luna`,
`reasoning_effort`, optional JSON response format, and bounded retries. Treat
that code as the starting point and work with any version already present in
the branch rather than replacing it from memory.

### Branch and boundaries

- Start from the accepted phase 32 result and create
  `phase-33-truthful-evaluation`.
- Read `AGENTS.md`, the tone section of `CLAUDE.md`, architecture, session and
  demo plans, and the phase 32 handover before editing.
- Preserve unrelated user changes. Do not read, edit, export, regenerate, or
  resolve files under `notebooks/` or `web/public/notebooks/`.
- Keep broad frontend component extraction for phase 36. You may extract a
  focused action or pure calculation when this phase needs it, but do not turn
  this into a general refactor.
- Update technical statements in the app, deck, and docs when this phase makes
  them false. Leave deck visual redesign and the general copy pass for phase
  35.

### 1. Tighten the Chat Completions boundary

Create one backend data boundary for OpenAI-compatible Chat Completions. All
game replies, scenario assessments, structured evaluations, and future text
jobs must go through it rather than constructing HTTP requests independently.

Required contract:

- Build the URL from `OPENAI_BASE_URL`, strip one trailing slash, and call
  `/chat/completions`.
- Send `messages` and a configurable `model`; keep `gpt-5.6-luna` as Ramon's
  current default unless a newer accepted repository decision changes it.
- Remove every active `gpt-5.5-mini` and stale `gpt-5.5` default, fixture,
  option, test, code snippet, and documentation reference. Do not silently map
  a nonexistent name to another model.
- Read text from `choices[0].message.content` and validate the response shape
  before indexing into it. Preserve the raw body needed for diagnostics and
  evaluation without storing API keys or authorization headers.
- Support optional JSON mode with
  `response_format={"type": "json_object"}`. If an otherwise compatible model
  explicitly rejects that capability, retry once without the field and make
  the fallback visible in attempt provenance. Do not treat every `400` as a
  response-format problem or hide malformed request bodies.
- Treat `reasoning_effort` as a model/provider capability rather than assuming
  every OpenAI-compatible endpoint accepts it. Keep capability decisions in a
  typed model catalog or request calculation, not scattered string checks.
- Use a 120-second upper bound or a documented smaller operation-specific
  timeout. Handle `httpx` transport failures as well as HTTP responses.
- Retry genuinely transient failures with bounded exponential backoff, jitter,
  and `Retry-After` where supplied. Retry `429` and `5xx`. Normally fail a
  `401` immediately, but preserve the observed workshop exception: the exact
  generic `401` message "You have insufficient permissions for this
  operation" may be retried once or twice when the key was recently created or
  changed, or when the same credential has already succeeded in the current
  process. Make the recent-key case an explicit documented opt-in rather than
  guessing from the response. Never retry invalid-key, revoked-key, IP-policy,
  or confirmed project/model-denial responses. Retain every failing
  `x-request-id`. Do not retry deterministic `400` errors after the one narrowly
  identified capability fallback.
- Include status, attempt number, provider request ID, and a bounded response
  excerpt in diagnostic errors. Never include the API key or entire possibly
  sensitive prompt/response by default.
- Keep parsing separate from transport. Structured tasks parse JSON in a pure
  calculation and retain the original text when parsing fails. Fence cleanup,
  if supported for non-JSON-mode providers, must be deterministic and tested.
- No code in this phase may introduce a Responses API call.

Use `httpx.MockTransport` or a small local fake HTTP endpoint to test the data
boundary itself. This is appropriate boundary testing, not mocking the whole
application. Cover success, malformed response shape, JSON-mode rejection then
success, unsupported `reasoning_effort`, `429` with retry, `500` exhaustion,
transport timeout, explicit invalid-key `401` without retry, generic transient
permissions `401` followed by success, exhausted transient `401` attempts with
all request IDs retained, and redacted diagnostics.

### 2. Define durable provenance before changing metrics

Write down the event and record model needed to answer these questions from
the database alone:

- Who attempted this move: participant, opponent model, presenter, fallback,
  or another explicit actor?
- Which model, provider alias, prompt version, game, ply, run, and adapter or
  checkpoint produced it?
- What raw response arrived, if any?
- Did parsing succeed? Was the parsed move syntactically valid and legal?
- Was another attempt made, and which attempt was finally applied?
- Which dataset snapshot and evaluation run consumed the record?

Use a schema migration that preserves existing databases. A separate immutable
model-attempt table may be cleaner than forcing failed replies into the moves
table. Choose the schema based on ownership and queries, not convenience in
one component. Repositories perform I/O only. Actions own the transaction and
business decisions.

Make a move, its resulting board state, generated dataset rows, game outcome,
and associated accepted model attempt atomic where they belong to one action.
Repository-level commits that leave half a move persisted are not acceptable.

### 3. Replace circular evaluations with real measurements

Redefine metrics over evidence they genuinely measure:

- Valid JSON rate must use raw responses from a task that asked for JSON. It
  must count parse failures and report numerator, denominator, and scope.
- Legal move rate must be filterable by actor, model, run/checkpoint, game, and
  evaluation window. Do not count participant moves as model successes.
- Metrics must retain source (`computed` or `cached`), definition/version,
  units, directionality, sample count, and enough provenance to reproduce the
  calculation.
- Empty samples return an explicit unavailable result, not a misleading zero
  or perfect score.
- Before/after comparisons use the same frozen input set and identify both
  model or adapter versions. Phase 34 will build the full visible adaptation
  loop, but the backend contract must support it now.

Keep the calculations pure. Give them explicit typed inputs and test boundary
conditions such as no attempts, unparsable output, duplicate retries, legal
but unaccepted output, and mixed actors.

Cached illustrative metrics may remain when real infrastructure is outside the
workshop, but their notes must survive seeding, storage, API serialization, and
rendering. Never label cached values as live.

### 4. Make dataset targets honest and teachable

Audit every dataset row created from a move and every corresponding deck or UI
label. For each format, document input, target, target type, when it becomes
known, and its intended training objective.

For `board_tensor_to_move_class`, either implement a deterministic documented
move vocabulary and persist the actual class index, or rename the field and
teach it as a UCI target. Do not show an invented integer disconnected from
the stored row.

For policy/value data, choose one of these honest designs:

- compute policy targets from a documented source and value from final game
  outcome or a real engine evaluation; or
- keep the immediate shaped reward but call it `move_reward`, explain that it
  is not a position value, and do not present it as AlphaZero-style data.

Whichever design you choose must work for unfinished games and must explain
when delayed outcome labels are backfilled. Make reward incentives explicit.
An ordinary legal move should not silently become evidence that a position is
good.

### 5. Persist the real-world scenario mapping

The scenario mapping is one of the workshop's distinctive datasets. Store it
against the relevant game and ply with assessment text, scenario text, model,
prompt version, creation time, and participant acceptance or edit state.

Required behavior:

- Reloading a workspace restores its prior assessments.
- A participant can accept or edit a suggested mapping without overwriting the
  raw model suggestion.
- Exports include the accepted scenario record and its provenance.
- Presenter room exports can distinguish raw suggestions from participant
  approved examples.
- Failed assessment calls have a recoverable explicit state and do not erase
  prior records.

Use a dedicated action and repository. Do not leave persistence orchestration
inside `WorkspacePanel`.

Call the shared Chat Completions boundary for this task with a terse system
message and an exact JSON object shape containing `assessment` and
`real_world`. Store the raw reply before parsing. Do not use the absence of a
provider key to invent a successful live mapping; show the existing cached or
skipped state accurately.

### 6. Give illegal model output a deterministic outcome

Implement a small explicit model-turn state machine. It must handle transport
failure, empty response, parse failure, illegal move, timeout, retry, fallback,
and terminal failure. Use a configurable low retry limit.

After the limit, choose and document a workshop-appropriate outcome such as a
forfeit or deterministic legal fallback. The board must never remain silently
stuck on the model's turn. Persist every failed attempt so the eval can count
it. The UI should state what happened in factual language and expose one clear
recovery action where manual recovery remains possible.

### Tests and acceptance

Use temporary databases and real chess calculations. Add migrations and tests
that prove:

1. Existing games migrate without losing moves.
2. Participant and model moves produce separate metrics.
3. Invalid JSON and illegal moves lower the correct metric denominator.
4. Retries retain all attempts but apply at most one move.
5. The terminal retry path cannot leave the game waiting forever.
6. Dataset row fields and visible labels agree for several legal moves,
   promotion, check, checkmate, and an unfinished game.
7. Scenario suggestions, edits, acceptance, reload, and export preserve both
   raw and approved values.
8. One action failure rolls back all state that should be atomic.
9. Every text-model workflow uses `/chat/completions`, and tests fail if a
   Responses API URL or `gpt-5.5-mini` reappears.
10. The narrow generic-permissions `401` exception retries successfully, while
    explicit credential and access denials do not retry.

Update frontend tests for the visible provenance and recovery states. Run
`just lint`, `just typecheck`, `just test`, and the relevant E2E paths. Manually
play the small-model failure path with the mock LLM configured to emit invalid
and illegal responses.

### Documentation and final report

Update `docs/architecture.md`, `docs/demo-plan.md`, dataset documentation, and
any deck statements made inaccurate by the old toy labels. Explain what is a
real metric, what remains cached, and what a denominator contains.

Create:

- `notes/ai/phase-33-truthful-evaluation.md`
- `notes/hu/phase-33-truthful-evaluation.md`

The handover must include the Chat Completions contract, capability fallbacks,
the evidence-based transient `401` exception, schema changes, transaction
boundaries, metric definitions, compatibility concerns, and exact tests run.
The learning guide must use the required Socratic/walkthrough ratio and should
make the human reason about why raw attempts and applied moves are different
records.

Finish with a concise summary including one example metric with its numerator,
denominator, actor/model scope, and provenance. Do not report success using
only fixture-based tests.
