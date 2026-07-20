# Dataset formats

Every applied legal move produces six dataset rows, one per training
approach the workshop teaches. This file is the contract: what each
row's input and target are, what type the target has, when it becomes
known, and what objective it trains. The stored payloads and the labels
in the dataset panel and deck must agree with this file; if they drift,
fix the code or fix this file, not neither.

Illegal attempts produce no dataset rows. A participant's illegal move
is still recorded in `moves` (reward -1, the RL lesson); a model's
illegal reply is recorded in `model_attempts`. Both feed evals, not
training data.

Every legal move does still get a `moves.actor`, and it is not always
`participant` or `model`: a `fallback` move is the deterministic
placeholder `actions/model_turn.py` plays (first legal move in UCI
sort order) when the model failed to answer within its retry budget.
It is a legal move for board and eval purposes, but it is not a
legitimate SFT target -- training on it would teach "always play the
alphabetically first legal move" as if that were skill.
`calculations/export.is_training_eligible` defines the eligible set as
`{participant, model}`; `chess_sft.jsonl` filters on it automatically.
`chess_all_shapes.jsonl`, the full archive, keeps every row including
ineligible ones for auditability, but tags each with `actor`, `model`,
`move_id`, `game_id`, and an explicit `training_eligible` boolean --
consumers must filter on that flag rather than assume every row in the
archive is trainable.

## pgn_prefix_to_move

- Input: the game so far as PGN move text, e.g. `1. e4 e5 2. Nf3`.
- Target: the next move in SAN (`target_san`), a string.
- Known: the moment the move is applied.
- Objective: next-token-style continuation (SFT). The model learns to
  continue a game script.

## fen_to_move

- Input: the position as a FEN string.
- Target: the played move as UCI and SAN, strings.
- Known: at move time.
- Objective: SFT on positions rather than histories.

## fen_legal_moves_to_move

- Input: FEN plus the full legal move list.
- Target: the played move in UCI, a string constrained to the list.
- Known: at move time.
- Objective: SFT where the environment does the rules and the model
  does the choosing. This is the shape the exported
  `chess_sft.jsonl` trains on.

## board_tensor_to_move_class

- Input: the board as 8x8x12 binary planes. The stored row carries the
  `fen` the tensor would be built from and the tensor's `shape`, not
  its values: the encoding is standard and cheap to regenerate from
  the stored fen, so the row is self-contained rather than depending
  on a value it doesn't hold.
- Target: `target_move_class`, an integer class index from the
  deterministic vocabulary in `calculations/move_vocab.py`:
  `class = from_square * 320 + to_square * 5 + promotion_code`,
  vocabulary size 20480. `target_uci` rides along so a human can check
  the inversion.
- Known: at move time.
- Objective: multi-class classification, the AlphaZero-style supervised
  policy head. The class index is real: the deck's example `3980` is
  `e2e4`, and `move_from_class` inverts any stored value.

## policy_move_reward

- Input: the position as a FEN string (`fen`), plus the legal move list
  as the `policy_target` keys. The legal move list alone is not the
  position -- the same set of legal moves can arise from more than one
  arrangement of pieces -- so the row carries the fen explicitly rather
  than expecting a consumer to reconstruct the board from move keys.
- Targets: `policy_target`, a one-hot distribution over the legal moves
  with all weight on the move actually played, and `move_reward`, an
  integer.
- Known: at move time. Nothing in the row waits for the game to end,
  which is why unfinished games produce complete rows.
- Objective: policy imitation plus a shaped per-move reward signal.

What this row is not: AlphaZero policy/value data. A search-derived
policy distribution needs an engine, and a position value needs the
final game outcome or an engine evaluation. This app runs neither and
does not invent either. `move_reward` scores the move that was made
(+1 legal, +2 check, +10 checkmate, -1 illegal at the move record
level), so an ordinary legal move earns +1 for being a legal action,
never a claim that the resulting position is good. If a future phase
wants outcome-based value targets, they must be backfilled at game end
and labelled as such.

## rl_trajectory

- Input/step: `state_fen`, `action_uci`, `reward`, `next_state_fen`,
  `done`.
- Known: at move time; `done` reflects whether that move ended the
  game.
- Objective: the gym formulation for RL. The reward here is the same
  shaped `move_reward`, and the incentive it encodes is explicit:
  checkmate dominates (+10), checks are mildly encouraged (+2), legal
  play earns +1 per move. A policy maximizing this without the
  checkmate bonus would happily play long aimless games; the bonus and
  the note in the row are the honest statement of that trade-off.

## Scenario mappings (chess_scenarios.jsonl)

Not per-move rows: one record per assessment call, stored in
`scenario_assessments` with the raw model suggestion immutable and the
participant's accepted or edited text separate. Exports carry both plus
model, provider alias, and prompt version. `approved` is null until a
participant reviewed the record, so raw model output and vetted
examples are never conflated.

## Frozen training snapshots (dataset_snapshots)

A snapshot is the durable, hashed form of the SFT export: the
`fen_legal_moves_to_move` rows converted through the same
`build_sft_rows` as `chess_sft.jsonl` (`{"prompt", "completion"}` per
row, schema `sft-prompt-completion-v1`, prompt contract `sft-v2`:
the prompt invites an optional in-JSON `why` explanation, while the
completions stay bare moves, which is exactly why an adapter trained
on them stops filling the field),
frozen at a moment in time with the rows stored inline. The
eligibility rule above applies at freeze time and the snapshot records
what it excluded rather than hiding it. Scenario mappings ride along
as separate raw and approved counts. `content_hash` is order-
independent and duplicate-preserving, the same recipe as
`position_set_id`; it is the identity an adapter's provenance points
at, which is why an adapter without a dataset hash is not
reproducible. Held-out evaluation suites (`eval_suites`) carry their
own hash over examples plus prompt contract; training refuses any
snapshot whose positions overlap a suite, because a model scored on
its own training examples is not being evaluated.
