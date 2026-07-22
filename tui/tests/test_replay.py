"""Replay is evidence: a fresh process reloads the stored game and the
cursor reproduces every recorded position, comment included."""

import chess
from conftest import fresh_connection, move_reply, scripted_client

from chess_tui.actions.game import apply_participant_move, play_model_turn, start_game
from chess_tui.actions.replay import list_history, open_replay
from chess_tui.calculations.moves import ParsedMove, parse_participant_move


def _play_short_game(conn, config):
    client, _ = scripted_client(
        config,
        [move_reply("e7e5", "Symmetry. Bold."), move_reply("b8c6", "A knight, developed.")],
    )
    state = start_game(conn, config.model, chess.WHITE, "tester")
    for white in ["e2e4", "g1f3"]:
        parsed = parse_participant_move(state.board.fen(), white)
        assert isinstance(parsed, ParsedMove)
        apply_participant_move(conn, state, parsed)
        play_model_turn(conn, state, client)
    client.close()
    return state


def test_replay_reproduces_every_stored_position_after_reload(conn, db_path, config):
    state = _play_short_game(conn, config)

    other = fresh_connection(db_path)
    cursor = open_replay(other, state.game_id)
    assert cursor is not None
    assert cursor.fen == chess.STARTING_FEN
    assert len(cursor.plies) == 4

    board = chess.Board()
    for ply in cursor.plies:
        cursor_index_before = cursor.index
        cursor.forward()
        assert cursor.index == cursor_index_before + 1
        board.push_uci(ply.uci)
        assert cursor.fen == board.fen()
    assert [p.san for p in cursor.plies] == ["e4", "e5", "Nf3", "Nc6"]
    assert cursor.plies[1].comment == "Symmetry. Bold."
    assert cursor.plies[3].comment == "A knight, developed."

    cursor.forward()  # walking past the end stays at the end
    assert cursor.index == 4
    cursor.back()
    assert cursor.index == 3
    other.close()


def test_history_is_newest_first(conn, config):
    first = _play_short_game(conn, config)
    second = _play_short_game(conn, config)
    items = list_history(conn)
    assert [item.game_id for item in items] == [second.game_id, first.game_id]
    assert all(item.move_count == 2 for item in items)


def test_open_replay_of_unknown_game_returns_none(conn):
    assert open_replay(conn, "nope") is None
