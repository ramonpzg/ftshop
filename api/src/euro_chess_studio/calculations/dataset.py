"""Pure functions that turn one applied move into the dataset row shapes
described in the workshop: the same chess position, encoded the way each
training approach actually consumes it.

Every field in these rows is real: the move class comes from the
documented vocabulary in move_vocab.py, and the shaped reward is called
move_reward because that is what it is. See docs/datasets.md for each
format's input, target, when the target becomes known, and its training
objective.
"""

from euro_chess_studio.calculations.move_vocab import (
    MOVE_VOCABULARY,
    VOCABULARY_SIZE,
    move_class_index,
)
from euro_chess_studio.calculations.reward import compute_reward
from euro_chess_studio.chess.board import MoveResult


def format_pgn_prefix(prior_sans: list[str]) -> str:
    """Renders prior moves as PGN move text, e.g. "1. e4 e5 2. Nf3"."""
    parts = []
    for i, san in enumerate(prior_sans):
        if i % 2 == 0:
            parts.append(f"{i // 2 + 1}. {san}")
        else:
            parts.append(san)
    return " ".join(parts)


def build_dataset_rows(
    prior_sans: list[str],
    legal_moves_before: list[str],
    move: MoveResult,
) -> list[dict]:
    """One applied legal move, encoded as every dataset shape from the workshop.

    Returns a list of {"shape": str, "payload": dict} rows. Only called for
    legal moves: an illegal move has no "target" to encode a dataset row
    around, though it's still recorded for the legal-move-rate eval.
    """
    reward = compute_reward(
        legal=move.legal, is_check=move.is_check, is_checkmate=move.is_checkmate
    )

    rows = [
        {
            "shape": "pgn_prefix_to_move",
            "payload": {
                "prefix": format_pgn_prefix(prior_sans),
                "target_san": move.san,
            },
        },
        {
            "shape": "fen_to_move",
            "payload": {
                "fen": move.fen_before,
                "target_uci": move.uci,
                "target_san": move.san,
            },
        },
        {
            "shape": "fen_legal_moves_to_move",
            "payload": {
                "fen": move.fen_before,
                "legal_moves": legal_moves_before,
                "target_uci": move.uci,
            },
        },
        {
            "shape": "board_tensor_to_move_class",
            "payload": {
                "note": (
                    "The serious supervised path encodes the board as a stack of "
                    "8x8 binary planes, one per piece type and color, not as a FEN "
                    "string. This row stores the fen the tensor would be built from "
                    "and the tensor's shape, not its values: the encoding is "
                    "standard and cheap to regenerate from the fen. The class index "
                    "is real and invertible via the vocabulary formula."
                ),
                "fen": move.fen_before,
                "tensor_shape": [8, 8, 12],
                "move_vocabulary": MOVE_VOCABULARY,
                "vocabulary_size": VOCABULARY_SIZE,
                "target_move_class": move_class_index(move.uci),
                "target_uci": move.uci,
            },
        },
        {
            "shape": "policy_move_reward",
            "payload": {
                "note": (
                    "The policy target is one-hot on the move actually played; a "
                    "search-derived distribution needs an engine this app does not "
                    "run. move_reward is the immediate shaped reward for this move, "
                    "not a position value: judging who is winning needs the final "
                    "game outcome or an engine evaluation, and neither is invented "
                    "here. Works for unfinished games because nothing in the row "
                    "waits on the result."
                ),
                "policy_target": {u: (1.0 if u == move.uci else 0.0) for u in legal_moves_before},
                "move_reward": reward,
            },
        },
        {
            "shape": "rl_trajectory",
            "payload": {
                "state_fen": move.fen_before,
                "action_uci": move.uci,
                "reward": reward,
                "next_state_fen": move.fen_after,
                "done": move.is_game_over,
            },
        },
    ]
    return rows
