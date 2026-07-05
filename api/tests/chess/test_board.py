import chess

from euro_chess_studio.chess.board import apply_move, get_legal_moves


def test_get_legal_moves_from_starting_position():
    moves = get_legal_moves(chess.STARTING_FEN)
    assert len(moves) == 20
    assert "e2e4" in moves


def test_apply_move_accepts_a_legal_opening_move():
    result = apply_move(chess.STARTING_FEN, "e2e4")
    assert result.legal is True
    assert result.san == "e4"
    assert result.fen_after != chess.STARTING_FEN
    assert result.is_check is False
    assert result.is_checkmate is False


def test_apply_move_rejects_an_illegal_move():
    result = apply_move(chess.STARTING_FEN, "e2e5")
    assert result.legal is False
    assert result.san is None
    assert result.fen_after == chess.STARTING_FEN


def test_apply_move_rejects_malformed_uci():
    result = apply_move(chess.STARTING_FEN, "not-a-move")
    assert result.legal is False
    assert result.fen_after == chess.STARTING_FEN


def test_apply_move_detects_check_without_mate():
    # Bishop d1-a4 puts the black king in check along an open diagonal,
    # with escape squares available, so this is check but not mate.
    fen = "4k3/8/8/8/8/8/8/3BK3 w - - 0 1"
    result = apply_move(fen, "d1a4")
    assert result.legal is True
    assert result.is_check is True
    assert result.is_checkmate is False


def test_apply_move_detects_checkmate():
    # Fool's mate: fastest checkmate in chess
    fen_after_f3_e5_g4 = "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2"
    result = apply_move(fen_after_f3_e5_g4, "d8h4")
    assert result.legal is True
    assert result.is_checkmate is True
    assert result.is_game_over is True
