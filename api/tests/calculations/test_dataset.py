import chess

from euro_chess_studio.calculations.dataset import build_dataset_rows, format_pgn_prefix
from euro_chess_studio.chess.board import apply_move, get_legal_moves


def test_format_pgn_prefix_pairs_white_and_black_moves():
    assert format_pgn_prefix(["e4", "e5", "Nf3"]) == "1. e4 e5 2. Nf3"


def test_format_pgn_prefix_handles_empty_history():
    assert format_pgn_prefix([]) == ""


def test_format_pgn_prefix_handles_single_move():
    assert format_pgn_prefix(["e4"]) == "1. e4"


def make_e4_row_set():
    legal_moves_before = get_legal_moves(chess.STARTING_FEN)
    move = apply_move(chess.STARTING_FEN, "e2e4")
    rows = build_dataset_rows([], legal_moves_before, move)
    return {row["shape"]: row["payload"] for row in rows}


def test_build_dataset_rows_returns_all_six_shapes():
    rows_by_shape = make_e4_row_set()
    assert set(rows_by_shape) == {
        "pgn_prefix_to_move",
        "fen_to_move",
        "fen_legal_moves_to_move",
        "board_tensor_to_move_class",
        "policy_value_to_move",
        "rl_trajectory",
    }


def test_pgn_prefix_row_uses_the_move_history_and_target():
    payload = make_e4_row_set()["pgn_prefix_to_move"]
    assert payload["prefix"] == ""
    assert payload["target_san"] == "e4"


def test_fen_to_move_row_carries_the_starting_fen_and_target():
    payload = make_e4_row_set()["fen_to_move"]
    assert payload["fen"] == chess.STARTING_FEN
    assert payload["target_uci"] == "e2e4"
    assert payload["target_san"] == "e4"


def test_fen_legal_moves_row_includes_all_twenty_opening_moves():
    payload = make_e4_row_set()["fen_legal_moves_to_move"]
    assert len(payload["legal_moves"]) == 20
    assert "e2e4" in payload["legal_moves"]


def test_rl_trajectory_row_has_state_action_reward_next_state_done():
    payload = make_e4_row_set()["rl_trajectory"]
    assert payload["state_fen"] == chess.STARTING_FEN
    assert payload["action_uci"] == "e2e4"
    assert payload["reward"] == 1
    assert payload["next_state_fen"] != chess.STARTING_FEN
    assert payload["done"] is False


def test_policy_value_row_puts_all_weight_on_the_played_move():
    payload = make_e4_row_set()["policy_value_to_move"]
    assert payload["policy_target"]["e2e4"] == 1.0
    assert payload["policy_target"]["a2a3"] == 0.0
    assert sum(payload["policy_target"].values()) == 1.0
