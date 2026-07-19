import chess
import pytest

from euro_chess_studio.calculations.move_vocab import (
    VOCABULARY_SIZE,
    move_class_index,
    move_from_class,
    square_index,
)


def test_square_indexing_matches_python_chess():
    assert square_index("a1") == chess.A1
    assert square_index("e2") == chess.E2
    assert square_index("h8") == chess.H8


def test_e2e4_has_a_deterministic_class():
    # from e2 (12) * 320 + to e4 (28) * 5 + no promotion (0)
    assert move_class_index("e2e4") == 12 * 320 + 28 * 5
    assert move_from_class(move_class_index("e2e4")) == "e2e4"


def test_promotions_round_trip():
    for uci in ["a7a8q", "a7a8r", "a7a8b", "a7a8n", "h2h1q"]:
        index = move_class_index(uci)
        assert 0 <= index < VOCABULARY_SIZE
        assert move_from_class(index) == uci


def test_every_legal_opening_move_round_trips():
    board = chess.Board()
    for move in board.legal_moves:
        uci = move.uci()
        assert move_from_class(move_class_index(uci)) == uci


def test_distinct_moves_get_distinct_classes():
    board = chess.Board()
    classes = {move_class_index(move.uci()) for move in board.legal_moves}
    assert len(classes) == board.legal_moves.count()


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError):
        move_class_index("castle")
    with pytest.raises(ValueError):
        move_class_index("i9i9")
    with pytest.raises(ValueError):
        move_from_class(VOCABULARY_SIZE)
