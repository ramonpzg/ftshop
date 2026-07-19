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
        "policy_move_reward",
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


def test_policy_move_reward_row_puts_all_weight_on_the_played_move():
    payload = make_e4_row_set()["policy_move_reward"]
    assert payload["policy_target"]["e2e4"] == 1.0
    assert payload["policy_target"]["a2a3"] == 0.0
    assert sum(payload["policy_target"].values()) == 1.0


def test_policy_move_reward_is_the_shaped_reward_not_a_position_value():
    payload = make_e4_row_set()["policy_move_reward"]
    assert payload["move_reward"] == 1
    assert "value_target" not in payload
    assert "not a position value" in payload["note"]


def test_board_tensor_row_stores_the_real_class_index():
    from euro_chess_studio.calculations.move_vocab import move_class_index, move_from_class

    payload = make_e4_row_set()["board_tensor_to_move_class"]
    assert payload["target_move_class"] == move_class_index("e2e4")
    assert move_from_class(payload["target_move_class"]) == payload["target_uci"] == "e2e4"
    assert payload["vocabulary_size"] == 20480
    assert payload["move_vocabulary"]


def rows_for(fen: str, uci: str) -> dict:
    legal_before = get_legal_moves(fen)
    move = apply_move(fen, uci)
    return {row["shape"]: row["payload"] for row in build_dataset_rows([], legal_before, move)}


def test_promotion_move_encodes_its_promotion_class():
    from euro_chess_studio.calculations.move_vocab import move_class_index

    # White pawn on a7, promotion to queen.
    payloads = rows_for("8/P7/8/8/8/6k1/8/6K1 w - - 0 1", "a7a8q")
    tensor = payloads["board_tensor_to_move_class"]
    assert tensor["target_uci"] == "a7a8q"
    assert tensor["target_move_class"] == move_class_index("a7a8q")
    assert payloads["policy_move_reward"]["move_reward"] == 1


def test_check_and_checkmate_rewards_are_explicit_move_rewards():
    # Scholar's mate final position: Qxf7 is checkmate.
    mate_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 4 4"
    mate = rows_for(mate_fen, "f3f7")
    assert mate["policy_move_reward"]["move_reward"] == 10
    assert mate["rl_trajectory"]["reward"] == 10
    assert mate["rl_trajectory"]["done"] is True

    check_fen = "rnbqkbnr/ppppp1pp/5p2/8/8/4P3/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
    check = rows_for(check_fen, "d1h5")
    assert check["policy_move_reward"]["move_reward"] == 2
    assert check["rl_trajectory"]["done"] is False


def test_unfinished_game_rows_are_complete_without_an_outcome():
    """Nothing in any row waits on the final result: an unfinished game
    produces the same complete fields as a finished one."""
    payloads = make_e4_row_set()
    assert payloads["rl_trajectory"]["done"] is False
    for shape, payload in payloads.items():
        assert None not in payload.values(), shape
