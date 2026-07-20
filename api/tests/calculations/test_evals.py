"""Boundary tests for the pure metric calculations: empty samples,
unparsable output, duplicate retries, legal-but-unapplied replies, and
mixed actors."""

import itertools

import pytest

from euro_chess_studio.calculations.evals import (
    compute_legal_move_rate,
    compute_model_legal_move_rate,
    compute_valid_json_rate,
)

_ids = itertools.count(1)


def move(actor: str, legal: bool) -> dict:
    return {"id": f"move_{next(_ids)}", "actor": actor, "is_legal": int(legal)}


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
) -> dict:
    return {
        "id": f"attempt_{next(_ids)}",
        "task": task,
        "actor": actor,
        "raw_response": raw,
        "is_legal": is_legal,
        "json_requested": int(json_requested),
        "model": model,
        "game_id": game_id,
        "checkpoint": checkpoint,
        "applied_move_id": applied_move_id,
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
    # The frozen input set is exactly the two participant moves, in
    # order -- auditable after the fact, not re-derived later.
    assert result.sample_ids == tuple(m["id"] for m in participant_moves)


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


def test_valid_json_rate_filters_by_model():
    attempts = [
        attempt(model="gemma-4-2b-local", raw="not json"),
        attempt(model="gpt-5.6-luna", raw='{"move": "e2e4"}'),
    ]
    result = compute_valid_json_rate(attempts, model="gemma-4-2b-local")
    assert result.denominator == 1
    assert result.value == 0.0
    assert result.scope["model"] == "gemma-4-2b-local"


def test_valid_json_rate_ignores_attempts_that_did_not_ask_for_json():
    attempts = [
        attempt(raw="plain prose", json_requested=False),
        attempt(raw='{"ok": true}'),
    ]
    result = compute_valid_json_rate(attempts)
    assert result.denominator == 1
    assert result.value == 1.0
