"""The load simulator's pure pieces: how it reads a model turn, what
it counts as an error, and the verdict it hands the operator. These
are what make a capacity run trustworthy enough to set ROOM_MODEL_PLAY
from, so they get real tests, not a shrug because "it's a tool"."""

from euro_chess_studio.tools.load_sim import (
    Verdict,
    build_verdict,
    interpret_model_turn,
    is_error_status,
)


def _move(fen_after: str = "after-fen", is_legal: bool = True) -> dict:
    return {"uci": "e7e5", "is_legal": is_legal, "fen_after": fen_after}


def test_a_model_move_outcome_advances_the_board():
    view = interpret_model_turn({"outcome": "model_move", "move": _move(), "game_result": None})
    assert view.outcome == "model_move"
    assert view.next_fen == "after-fen"
    assert view.game_over is False


def test_a_fallback_move_outcome_advances_the_board():
    view = interpret_model_turn(
        {"outcome": "fallback_move", "move": _move("fallback-fen"), "game_result": None}
    )
    assert view.outcome == "fallback_move"
    assert view.next_fen == "fallback-fen"


def test_an_unavailable_outcome_has_no_move_and_does_not_crash():
    """Reproduces the reported bug: unavailable is HTTP 200 with move
    null, and the simulator used to index into it and die, exactly on
    the runs where the room was overloaded."""
    view = interpret_model_turn(
        {"outcome": "unavailable", "move": None, "game_result": None, "detail": "no reply"}
    )
    assert view.outcome == "unavailable"
    assert view.next_fen is None
    assert view.game_over is False


def test_a_stale_outcome_has_no_move_and_does_not_crash():
    view = interpret_model_turn(
        {"outcome": "stale", "move": None, "game_result": None, "detail": "board changed"}
    )
    assert view.outcome == "stale"
    assert view.next_fen is None


def test_a_finished_game_is_flagged_regardless_of_outcome():
    view = interpret_model_turn({"outcome": "model_move", "move": _move(), "game_result": "loss"})
    assert view.game_over is True


def test_every_non_2xx_is_an_error():
    """4xx used to be invisible: a run where every model move was
    refused 403 reported an error column of zero."""
    assert is_error_status(0) is True
    assert is_error_status(403) is True
    assert is_error_status(409) is True
    assert is_error_status(500) is True
    assert is_error_status(200) is False
    assert is_error_status(201) is False


def _samples(latencies_ms: list[float], status: int = 200) -> list[tuple[float, int]]:
    return [(ms, status) for ms in latencies_ms]


def test_the_verdict_passes_a_fast_clean_run():
    verdict = build_verdict(
        _samples([500.0] * 20),
        {"model_move": 18, "fallback_move": 2},
        turn_deadline_seconds=30.0,
    )
    assert verdict.passed is True
    assert any("PASS" in line for line in verdict.lines)
    # Fallbacks are the model answering badly, not the server failing;
    # they are reported but do not fail the verdict.
    assert any("2 fallback_move" in line for line in verdict.lines)


def test_the_verdict_fails_when_p95_exceeds_the_turn_deadline():
    verdict = build_verdict(
        _samples([31_000.0] * 20),
        {"model_move": 20},
        turn_deadline_seconds=30.0,
    )
    assert verdict.passed is False
    assert any("exceeds" in line for line in verdict.lines)


def test_the_verdict_fails_on_unavailable_or_stale_turns():
    verdict = build_verdict(
        _samples([500.0] * 20),
        {"model_move": 15, "unavailable": 4, "stale": 1},
        turn_deadline_seconds=30.0,
    )
    assert verdict.passed is False
    assert any("4 unavailable and 1 stale" in line for line in verdict.lines)


def test_the_verdict_fails_on_model_move_errors():
    samples = _samples([500.0] * 19) + [(500.0, 403)]
    verdict = build_verdict(samples, {"model_move": 19}, turn_deadline_seconds=30.0)
    assert verdict.passed is False
    assert any("1 model-move error" in line for line in verdict.lines)


def test_a_run_with_no_model_traffic_cannot_certify():
    """The mock-less backend run must say so instead of passing by
    vacuous truth: zero errors over zero model calls proves nothing."""
    verdict = build_verdict([], {}, turn_deadline_seconds=30.0)
    assert verdict.passed is None
    assert any("cannot certify" in line for line in verdict.lines)
    assert isinstance(verdict, Verdict)
