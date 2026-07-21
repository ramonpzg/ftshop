"""The truthful game loop, driven through real actions with a scripted
transport: python-chess adjudicates, persistence happens before the
next network call, and endings land in the record."""

import json

import pytest
from conftest import fresh_connection, move_reply, scripted_client

from chess_tui.actions.game import (
    AppliedMove,
    apply_participant_move,
    play_model_turn,
    start_game,
)
from chess_tui.calculations.moves import ParsedMove, parse_participant_move
from chess_tui.calculations.stats import compute_record
from chess_tui.data import games_repo, plies_repo


def _move(conn, state, text):
    parsed = parse_participant_move(state.board.fen(), text)
    assert isinstance(parsed, ParsedMove), parsed
    return apply_participant_move(conn, state, parsed)


def test_participant_move_is_committed_before_any_model_call(conn, db_path, config):
    client, scripted = scripted_client(config, [])
    state = start_game(conn, config.model)
    _move(conn, state, "e2e4")
    other = fresh_connection(db_path)
    rows = plies_repo.plies_for_game(other, state.game_id)
    assert [row["uci"] for row in rows] == ["e2e4"]
    assert scripted.requests == []
    other.close()
    client.close()


def test_model_turn_applies_a_legal_reply_with_comment(conn, config):
    client, scripted = scripted_client(config, [move_reply("e7e5", "Symmetry, obviously.")])
    state = start_game(conn, config.model)
    _move(conn, state, "e2e4")
    result = play_model_turn(conn, state, client)
    assert isinstance(result, AppliedMove)
    assert result.uci == "e7e5"
    assert state.board.fen().startswith("rnbqkbnr/pppp1ppp/8/4p3")
    assert state.last_comment == "Symmetry, obviously."
    client.close()


def test_request_body_is_bounded_and_schema_constrained(conn, config):
    client, scripted = scripted_client(config, [move_reply("e7e5")])
    state = start_game(conn, config.model)
    _move(conn, state, "e2e4")
    play_model_turn(conn, state, client)
    body = json.loads(scripted.requests[0].content)
    assert body["stream"] is False
    assert body["model"] == config.model
    assert "reasoning_effort" not in body
    assert body["response_format"]["type"] == "json_schema"
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["required"] == ["move", "comment"]
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert "LEGAL_MOVES:" in body["messages"][1]["content"]
    assert "- e7e5 | e5" in body["messages"][1]["content"]
    client.close()


def test_scholars_mate_records_a_win_and_captures(conn, db_path, config):
    client, _ = scripted_client(
        config, [move_reply("e7e5"), move_reply("b8c6"), move_reply("g8f6")]
    )
    state = start_game(conn, config.model)
    for white in ["e2e4", "d1h5", "f1c4"]:
        _move(conn, state, white)
        play_model_turn(conn, state, client)
    applied = _move(conn, state, "h5f7")
    assert applied.game_over
    assert state.result == "1-0"
    assert state.termination == "checkmate"

    other = fresh_connection(db_path)
    game = games_repo.get_game(other, state.game_id)
    assert game["result"] == "1-0"
    assert game["ended_at"] is not None
    assert game["duration_seconds"] is not None
    record = compute_record(
        games_repo.game_results(other), plies_repo.participant_captures_by_game(other)
    )
    assert record.wins == 1
    assert record.captures_in_wins == 1  # Qxf7#
    other.close()
    client.close()


def test_loyd_stalemate_records_a_draw(conn, db_path, config):
    black = ["a7a5", "a8a6", "h7h5", "a6h6", "f7f6", "e8f7", "d8d3", "d3h7", "f7g6"]
    white = ["e2e3", "d1h5", "h5a5", "a5c7", "h2h4", "c7d7", "d7b7", "b7b8", "b8c8", "c8e6"]
    client, _ = scripted_client(config, [move_reply(uci) for uci in black])
    state = start_game(conn, config.model)
    for uci in white:
        applied = _move(conn, state, uci)
        if applied.game_over:
            break
        play_model_turn(conn, state, client)
    assert state.over
    assert state.result == "1/2-1/2"
    assert state.termination == "stalemate"
    other = fresh_connection(db_path)
    record = compute_record(
        games_repo.game_results(other), plies_repo.participant_captures_by_game(other)
    )
    assert record.draws == 1
    other.close()
    client.close()


def test_fivefold_repetition_ends_the_game(conn, config):
    client, _ = scripted_client(config, [move_reply(uci) for uci in ["g8f6", "f6g8"] * 5])
    state = start_game(conn, config.model)
    for white_uci in ["g1f3", "f3g1"] * 5:
        _move(conn, state, white_uci)
        play_model_turn(conn, state, client)
        if state.over:
            break
    assert state.over
    assert state.result == "1/2-1/2"
    assert state.termination == "fivefold repetition"
    client.close()


def test_model_turn_refuses_when_it_is_not_blacks_turn(conn, config):
    client, scripted = scripted_client(config, [])
    state = start_game(conn, config.model)
    with pytest.raises(ValueError):
        play_model_turn(conn, state, client)
    assert scripted.requests == []
    client.close()
