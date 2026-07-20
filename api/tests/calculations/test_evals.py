"""Boundary tests for the pure metric calculations: empty samples,
unparsable output, duplicate retries, legal-but-unapplied replies, and
mixed actors."""

import itertools

import pytest

from euro_chess_studio.calculations.evals import (
    compute_legal_move_rate,
    compute_model_legal_move_rate,
    compute_position_set_id,
    compute_valid_json_rate,
)

_ids = itertools.count(1)


def move(actor: str, legal: bool, *, fen_before: str | None = None) -> dict:
    idx = next(_ids)
    return {
        "id": f"move_{idx}",
        "actor": actor,
        "is_legal": int(legal),
        "fen_before": fen_before or f"fen_{idx}",
    }


def attempt(
    *,
    task: str = "move",
    actor: str = "model",
    raw: str | None = '{"move": "e2e4"}',
    is_legal: int | None = None,
    json_requested: bool = True,
    model: str = "gpt-5.6-luna",
    game_id: str | None = None,
    checkpoint: str | None = None,
    applied_move_id: str | None = None,
    fen: str | None = None,
) -> dict:
    idx = next(_ids)
    return {
        "id": f"attempt_{idx}",
        "task": task,
        "actor": actor,
        "raw_response": raw,
        "is_legal": is_legal,
        "json_requested": int(json_requested),
        "model": model,
        "game_id": game_id,
        "checkpoint": checkpoint,
        "applied_move_id": applied_move_id,
        "fen": fen or f"fen_{idx}",
    }


def test_legal_move_rate_with_no_moves_is_unavailable():
    result = compute_legal_move_rate([])
    assert result.available is False
    assert result.value is None
    assert result.denominator == 0


def test_legal_move_rate_counts_only_the_requested_actor():
    participant_moves = [move("participant", True), move("participant", False)]
    other_moves = [move("model", True), move("fallback", True), move("unknown", False)]
    result = compute_legal_move_rate(participant_moves + other_moves, actor="participant")
    assert result.available is True
    assert result.value == 0.5
    assert result.numerator == 1
    assert result.denominator == 2
    assert result.scope == {"actor": "participant"}
    assert result.direction == "higher_is_better"
    assert result.unit == "ratio"
    # The audit trail is exactly the two participant moves, in order.
    assert result.sample_ids == tuple(m["id"] for m in participant_moves)
    assert result.positions == tuple(m["fen_before"] for m in participant_moves)


def test_legal_move_rate_for_only_other_actors_is_unavailable_not_perfect():
    result = compute_legal_move_rate([move("model", True)], actor="participant")
    assert result.available is False
    assert result.value is None


def test_model_legal_move_rate_excludes_transport_failures_from_the_denominator():
    attempts = [
        attempt(raw=None),  # transport failure: the model never answered
        attempt(raw='{"move": "e2e4"}', is_legal=1),
        attempt(raw='{"move": "e2e5"}', is_legal=0),
    ]
    result = compute_model_legal_move_rate(attempts)
    assert result.value == 0.5
    assert result.numerator == 1
    assert result.denominator == 2


def test_model_legal_move_rate_counts_every_duplicate_retry():
    attempts = [
        attempt(raw='{"move": "e2e5"}', is_legal=0),
        attempt(raw='{"move": "e2e5"}', is_legal=0),
        attempt(raw='{"move": "d2d4"}', is_legal=1),
    ]
    result = compute_model_legal_move_rate(attempts)
    assert result.value == pytest.approx(1 / 3)
    assert result.denominator == 3


def test_model_legal_move_rate_counts_legal_but_unapplied_replies():
    # A legal reply that never became the applied move (a later attempt
    # won) is still evidence the model produced a legal move.
    attempts = [attempt(raw='{"move": "d2d4"}', is_legal=1, applied_move_id=None)]
    result = compute_model_legal_move_rate(attempts)
    assert result.value == 1.0


def test_model_legal_move_rate_excludes_fallback_and_scenario_rows():
    attempts = [
        attempt(actor="fallback", raw=None, is_legal=1),
        attempt(task="scenario", raw="{}", is_legal=None),
    ]
    result = compute_model_legal_move_rate(attempts)
    assert result.available is False


def test_model_legal_move_rate_filters_by_model_and_game():
    attempts = [
        attempt(model="gemma-4-2b-local", game_id="game_1", is_legal=0),
        attempt(model="gpt-5.6-luna", game_id="game_1", is_legal=1),
        attempt(model="gemma-4-2b-local", game_id="game_2", is_legal=1),
    ]
    gemma = compute_model_legal_move_rate(attempts, model="gemma-4-2b-local")
    assert gemma.denominator == 2 and gemma.numerator == 1
    assert gemma.scope["model"] == "gemma-4-2b-local"
    game_one_gemma = compute_model_legal_move_rate(
        attempts, model="gemma-4-2b-local", game_id="game_1"
    )
    assert game_one_gemma.denominator == 1 and game_one_gemma.numerator == 0


def test_model_legal_move_rate_filters_by_checkpoint():
    attempts = [
        attempt(model="gemma-4-2b-local", checkpoint="base", is_legal=0, fen="p1"),
        attempt(model="gemma-4-2b-local", checkpoint="adapter", is_legal=1, fen="p1"),
    ]
    base = compute_model_legal_move_rate(attempts, model="gemma-4-2b-local", checkpoint="base")
    adapter = compute_model_legal_move_rate(
        attempts, model="gemma-4-2b-local", checkpoint="adapter"
    )
    assert base.denominator == 1 and base.numerator == 0
    assert adapter.denominator == 1 and adapter.numerator == 1
    # Same model, same position, different checkpoint: comparable, and
    # distinguishable in scope.
    assert base.scope["checkpoint"] == "base"
    assert adapter.scope["checkpoint"] == "adapter"
    assert compute_position_set_id(base.positions) == compute_position_set_id(adapter.positions)


def test_valid_json_rate_with_no_attempts_is_unavailable():
    result = compute_valid_json_rate([])
    assert result.available is False
    assert result.value is None


def test_valid_json_rate_measures_raw_replies_not_app_serialization():
    attempts = [
        attempt(raw='{"move": "e2e4"}'),
        attempt(raw="I would castle early."),
        attempt(raw='```json\n{"move": "d2d4"}\n```'),
        attempt(raw=None),  # no reply arrived; not in the denominator
    ]
    result = compute_valid_json_rate(attempts, task="move")
    assert result.value == pytest.approx(2 / 3)
    assert result.numerator == 2
    assert result.denominator == 3
    assert result.scope == {"json_requested": True, "task": "move"}
    assert result.sample_ids == tuple(a["id"] for a in attempts[:3])
    assert result.positions == tuple(a["fen"] for a in attempts[:3])


def test_valid_json_rate_filters_by_model():
    attempts = [
        attempt(model="gemma-4-2b-local", raw="not json"),
        attempt(model="gpt-5.6-luna", raw='{"move": "e2e4"}'),
    ]
    result = compute_valid_json_rate(attempts, model="gemma-4-2b-local")
    assert result.denominator == 1
    assert result.value == 0.0
    assert result.scope["model"] == "gemma-4-2b-local"


def test_valid_json_rate_filters_by_checkpoint():
    """Reproduces the reported bug: with one model and base/adapter
    checkpoints in play, valid_json_rate used to have no checkpoint
    filter at all, so a single unscoped row silently pooled attempts
    from both checkpoints."""
    attempts = [
        attempt(model="gemma-4-2b-local", checkpoint="base", raw="not json", fen="p1"),
        attempt(model="gemma-4-2b-local", checkpoint="adapter", raw='{"move": "e2e4"}', fen="p1"),
    ]
    base = compute_valid_json_rate(attempts, model="gemma-4-2b-local", checkpoint="base")
    adapter = compute_valid_json_rate(attempts, model="gemma-4-2b-local", checkpoint="adapter")
    assert base.denominator == 1 and base.value == 0.0
    assert adapter.denominator == 1 and adapter.value == 1.0
    assert base.scope["checkpoint"] == "base"
    assert adapter.scope["checkpoint"] == "adapter"


def test_valid_json_rate_ignores_attempts_that_did_not_ask_for_json():
    attempts = [
        attempt(raw="plain prose", json_requested=False),
        attempt(raw='{"ok": true}'),
    ]
    result = compute_valid_json_rate(attempts)
    assert result.denominator == 1
    assert result.value == 1.0


def test_compute_position_set_id_is_order_and_duplicate_independent():
    forward = compute_position_set_id(["fen-a", "fen-b"])
    backward = compute_position_set_id(["fen-b", "fen-a"])
    with_duplicates = compute_position_set_id(["fen-a", "fen-b", "fen-a"])
    assert forward == backward == with_duplicates
    assert forward is not None


def test_compute_position_set_id_differs_for_different_position_sets():
    assert compute_position_set_id(["fen-a", "fen-b"]) != compute_position_set_id(
        ["fen-a", "fen-c"]
    )


def test_compute_position_set_id_of_empty_set_is_none():
    assert compute_position_set_id([]) is None
    assert compute_position_set_id([None, None]) is None


def test_two_models_over_the_same_positions_get_the_same_position_set_id():
    """The concrete guarantee the frozen-input-set contract provides:
    two different models measured over the identical positions can
    prove it, rather than a reader having to trust matching scope."""
    shared_positions = ["start", "after-e4", "after-e4-e5"]
    base_attempts = [
        attempt(model="gpt-5.6-luna", checkpoint="base", is_legal=1, fen=fen)
        for fen in shared_positions
    ]
    adapted_attempts = [
        attempt(model="gpt-5.6-luna", checkpoint="adapter", is_legal=1, fen=fen)
        for fen in shared_positions
    ]
    base_result = compute_model_legal_move_rate(
        base_attempts, model="gpt-5.6-luna", checkpoint="base"
    )
    adapted_result = compute_model_legal_move_rate(
        adapted_attempts, model="gpt-5.6-luna", checkpoint="adapter"
    )
    assert compute_position_set_id(base_result.positions) == compute_position_set_id(
        adapted_result.positions
    )

    # A run over a different (even overlapping) position set must not
    # silently claim comparability.
    different_attempts = [
        attempt(model="gpt-5.6-luna", checkpoint="adapter", is_legal=1, fen=fen)
        for fen in [*shared_positions, "after-nf3"]
    ]
    different_result = compute_model_legal_move_rate(
        different_attempts, model="gpt-5.6-luna", checkpoint="adapter"
    )
    assert compute_position_set_id(base_result.positions) != compute_position_set_id(
        different_result.positions
    )
