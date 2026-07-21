"""Participant input: UCI and SAN, promotion in both spellings, and
rejections that never touch the board."""

import chess

from chess_tui.calculations.moves import (
    MoveRejection,
    ParsedMove,
    legal_moves_uci_san,
    parse_participant_move,
    san_history_text,
)

START = chess.STARTING_FEN
PROMOTION_FEN = "8/P6k/8/8/8/8/8/K7 w - - 0 1"


def test_uci_move_parses():
    parsed = parse_participant_move(START, "e2e4")
    assert parsed == ParsedMove(uci="e2e4", san="e4")


def test_san_move_parses():
    parsed = parse_participant_move(START, "Nf3")
    assert parsed == ParsedMove(uci="g1f3", san="Nf3")


def test_capitalized_uci_from_a_phone_keyboard_parses():
    parsed = parse_participant_move(START, "E2e4")
    assert isinstance(parsed, ParsedMove)
    assert parsed.uci == "e2e4"


def test_capitalized_pawn_san_gets_one_lowercase_retry():
    parsed = parse_participant_move(START, "E4")
    assert parsed == ParsedMove(uci="e2e4", san="e4")


def test_uci_promotion():
    parsed = parse_participant_move(PROMOTION_FEN, "a7a8q")
    assert parsed == ParsedMove(uci="a7a8q", san="a8=Q")


def test_san_promotion():
    parsed = parse_participant_move(PROMOTION_FEN, "a8=N")
    assert parsed == ParsedMove(uci="a7a8n", san="a8=N")


def test_promotion_without_a_piece_gets_a_hint():
    parsed = parse_participant_move(PROMOTION_FEN, "a7a8")
    assert isinstance(parsed, MoveRejection)
    assert parsed.kind == "illegal"
    assert "a7a8q" in parsed.detail


def test_illegal_uci_is_rejected():
    parsed = parse_participant_move(START, "e2e5")
    assert isinstance(parsed, MoveRejection)
    assert parsed.kind == "illegal"


def test_illegal_san_is_rejected():
    parsed = parse_participant_move(START, "Qh5")
    assert isinstance(parsed, MoveRejection)
    assert parsed.kind == "illegal"


def test_ambiguous_san_is_named_ambiguous():
    fen = "k7/8/8/8/8/8/1K6/R6R w - - 0 1"
    parsed = parse_participant_move(fen, "Rd1")
    assert isinstance(parsed, MoveRejection)
    assert parsed.kind == "ambiguous"


def test_gibberish_is_unrecognized():
    parsed = parse_participant_move(START, "banana")
    assert isinstance(parsed, MoveRejection)
    assert parsed.kind == "unrecognized"


def test_san_history_numbering():
    assert san_history_text([]) == "-"
    assert san_history_text(["e4"]) == "1. e4"
    assert san_history_text(["e4", "e5", "Nf3"]) == "1. e4 e5 2. Nf3"


def test_legal_moves_are_sorted_by_uci_and_paired_with_san():
    moves = legal_moves_uci_san(START)
    assert len(moves) == 20
    assert moves == sorted(moves, key=lambda pair: pair[0])
    assert ("e2e4", "e4") in moves
    assert ("g1f3", "Nf3") in moves
