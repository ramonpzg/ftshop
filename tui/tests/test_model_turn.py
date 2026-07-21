"""The failure policy: one corrective request for a reply that arrived
but failed validation, no silent fallback ever, the board unchanged on
failure, retry repeating the turn, and every raw reply persisted. The
transport boundary is httpx.MockTransport; nothing above it is mocked."""

import httpx
import pytest
from conftest import fresh_connection, move_reply, scripted_client

from chess_tui.actions.game import (
    AppliedMove,
    TurnFailure,
    apply_participant_move,
    play_model_turn,
    start_game,
)
from chess_tui.calculations.moves import ParsedMove, parse_participant_move
from chess_tui.data import attempts_repo


@pytest.fixture
def after_e4(conn, config):
    def _start(script):
        client, scripted = scripted_client(config, script)
        state = start_game(conn, config.model)
        parsed = parse_participant_move(state.board.fen(), "e2e4")
        assert isinstance(parsed, ParsedMove)
        apply_participant_move(conn, state, parsed)
        return state, client, scripted

    return _start


def test_malformed_then_valid_corrective_reply_applies(after_e4, conn):
    state, client, scripted = after_e4(["no json here", move_reply("e7e5", "Fixed.")])
    result = play_model_turn(conn, state, client)
    assert isinstance(result, AppliedMove)
    assert result.uci == "e7e5"

    corrective_body = scripted.requests[1].content.decode()
    assert "rejected" in corrective_body
    assert "no json here" in corrective_body
    assert "LEGAL_MOVES" in corrective_body

    attempts = attempts_repo.attempts_for_game(conn, state.game_id)
    assert [row["status"] for row in attempts] == ["malformed_json", "applied"]
    assert [row["corrective"] for row in attempts] == [0, 1]
    assert attempts[0]["raw_reply"] == "no json here"
    client.close()


def test_illegal_reply_gets_a_corrective_naming_the_move(after_e4, conn):
    state, client, scripted = after_e4(
        [move_reply("e2e4", "I like this square."), move_reply("g8f6", "Fine.")]
    )
    result = play_model_turn(conn, state, client)
    assert isinstance(result, AppliedMove)
    corrective_body = scripted.requests[1].content.decode()
    assert 'move \\"e2e4\\" is not in LEGAL_MOVES' in corrective_body
    attempts = attempts_repo.attempts_for_game(conn, state.game_id)
    assert [row["status"] for row in attempts] == ["illegal", "applied"]
    assert attempts[0]["parsed_move"] == "e2e4"
    client.close()


def test_two_invalid_replies_leave_the_board_unchanged(after_e4, conn, db_path):
    state, client, _ = after_e4(["garbage", '{"move": "a1a1", "comment": "sure"}'])
    fen_before = state.board.fen()
    result = play_model_turn(conn, state, client)
    assert isinstance(result, TurnFailure)
    assert result.code == "invalid_reply"
    assert state.board.fen() == fen_before
    assert state.pending_failure is result

    other = fresh_connection(db_path)
    plies = other.execute("SELECT uci FROM plies WHERE game_id = ?", (state.game_id,))
    assert [row["uci"] for row in plies] == ["e2e4"]
    attempts = attempts_repo.attempts_for_game(other, state.game_id)
    assert [row["status"] for row in attempts] == ["malformed_json", "illegal"]
    assert attempts[0]["raw_reply"] == "garbage"
    other.close()
    client.close()


def test_retry_after_two_invalid_replies_repeats_the_turn(after_e4, conn):
    state, client, scripted = after_e4(
        ["junk", "more junk", move_reply("e7e5", "Third time lucky, for you.")]
    )
    failure = play_model_turn(conn, state, client)
    assert isinstance(failure, TurnFailure)
    result = play_model_turn(conn, state, client)
    assert isinstance(result, AppliedMove)
    attempts = attempts_repo.attempts_for_game(conn, state.game_id)
    assert [row["attempt"] for row in attempts] == [1, 2, 3]
    assert [row["status"] for row in attempts] == ["malformed_json", "malformed_json", "applied"]
    assert state.pending_failure is None
    client.close()


def test_transport_failure_leaves_the_board_unchanged_with_retry(after_e4, conn):
    state, client, _ = after_e4([httpx.ConnectError("connection refused"), move_reply("e7e5")])
    fen_before = state.board.fen()
    failure = play_model_turn(conn, state, client)
    assert isinstance(failure, TurnFailure)
    assert failure.code == "unreachable"
    assert state.board.fen() == fen_before

    attempts = attempts_repo.attempts_for_game(conn, state.game_id)
    assert [row["status"] for row in attempts] == ["transport_failed"]
    assert attempts[0]["raw_reply"] is None

    result = play_model_turn(conn, state, client)
    assert isinstance(result, AppliedMove)
    assert result.uci == "e7e5"
    client.close()


def test_timeout_is_a_distinct_state(after_e4, conn):
    state, client, _ = after_e4([httpx.ReadTimeout("too slow")])
    failure = play_model_turn(conn, state, client)
    assert isinstance(failure, TurnFailure)
    assert failure.code == "timeout"
    attempts = attempts_repo.attempts_for_game(conn, state.game_id)
    assert attempts[0]["status"] == "timeout"
    client.close()


def test_http_error_is_a_distinct_state_with_bounded_detail(after_e4, conn):
    state, client, _ = after_e4([httpx.Response(500, text="boom " * 200)])
    failure = play_model_turn(conn, state, client)
    assert isinstance(failure, TurnFailure)
    assert failure.code == "http_error"
    assert "HTTP 500" in failure.detail
    assert len(failure.detail) < 300
    client.close()


def test_a_transport_failure_on_the_corrective_request_is_reported(after_e4, conn):
    state, client, _ = after_e4(["not json", httpx.ConnectError("gone")])
    failure = play_model_turn(conn, state, client)
    assert isinstance(failure, TurnFailure)
    assert failure.code == "unreachable"
    attempts = attempts_repo.attempts_for_game(conn, state.game_id)
    assert [row["status"] for row in attempts] == ["malformed_json", "transport_failed"]
    assert [row["corrective"] for row in attempts] == [0, 1]
    client.close()


def test_empty_content_is_judged_malformed_not_crashed(after_e4, conn):
    empty = httpx.Response(200, json={"choices": [{"message": {"content": None}}]})
    state, client, _ = after_e4([empty, move_reply("e7e5")])
    result = play_model_turn(conn, state, client)
    assert isinstance(result, AppliedMove)
    attempts = attempts_repo.attempts_for_game(conn, state.game_id)
    assert attempts[0]["status"] == "malformed_json"
    client.close()


def test_no_api_key_or_auth_header_ever_reaches_disk(conn, db_path):
    from chess_tui.data.config import Config

    secret_config = Config(db_path=db_path, api_key="sk-super-secret-750", no_color=True)
    client, scripted = scripted_client(secret_config, ["oops", httpx.ConnectError("down")])
    state = start_game(conn, secret_config.model)
    parsed = parse_participant_move(state.board.fen(), "e2e4")
    assert isinstance(parsed, ParsedMove)
    apply_participant_move(conn, state, parsed)
    play_model_turn(conn, state, client)
    conn.commit()

    sent = scripted.requests[0].headers.get("authorization")
    assert sent == "Bearer sk-super-secret-750"  # it is sent, and only sent
    raw = db_path.read_bytes()
    assert b"sk-super-secret-750" not in raw
    assert b"Authorization" not in raw
    assert b"Bearer" not in raw
    assert "sk-super-secret-750" not in repr(secret_config)
    client.close()
