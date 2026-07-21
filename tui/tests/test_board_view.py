"""The board's plain text form is the alignment contract: exact lines,
stable three-character cells, and file letters sitting over pieces."""

import chess

from chess_tui.calculations.board_view import BOARD_WIDTH, board_grid, board_lines

AFTER_E4 = [
    "    a  b  c  d  e  f  g  h",
    " 8  r  n  b  q  k  b  n  r  8",
    " 7  p  p  p  p  p  p  p  p  7",
    " 6  .  .  .  .  .  .  .  .  6",
    " 5  .  .  .  .  .  .  .  .  5",
    " 4  .  .  .  .  P  .  .  .  4",
    " 3  .  .  .  .  .  .  .  .  3",
    " 2  P  P  P  P  .  P  P  P  2",
    " 1  R  N  B  Q  K  B  N  R  1",
    "    a  b  c  d  e  f  g  h",
]


def _fen_after(ucis: list[str]) -> str:
    board = chess.Board()
    for uci in ucis:
        board.push_uci(uci)
    return board.fen()


def test_reference_position_renders_exactly():
    lines = board_lines(board_grid(_fen_after(["e2e4"]), "e2e4"))
    assert lines == AFTER_E4


def test_every_line_fits_the_fixed_width():
    fen = _fen_after(["e2e4", "e7e5", "g1f3", "b8c6"])
    lines = board_lines(board_grid(fen))
    assert max(len(line) for line in lines) == BOARD_WIDTH
    assert BOARD_WIDTH == 29


def test_file_letters_sit_exactly_over_pieces():
    lines = board_lines(board_grid(chess.STARTING_FEN))
    for file_index, letter in enumerate("abcdefgh"):
        column = lines[0].index(letter)
        assert lines[1][column] == "rnbqkbnr"[file_index]
        assert lines[8][column] == "RNBQKBNR"[file_index]


def test_white_is_uppercase_and_black_is_lowercase():
    lines = board_lines(board_grid(chess.STARTING_FEN))
    assert "R  N  B  Q  K  B  N  R" in lines[8]
    assert "r  n  b  q  k  b  n  r" in lines[1]


def test_flip_puts_white_at_the_top_and_reverses_files():
    lines = board_lines(board_grid(chess.STARTING_FEN, flipped=True))
    assert lines[0] == "    h  g  f  e  d  c  b  a"
    assert lines[1] == " 1  R  N  B  K  Q  B  N  R  1"
    assert lines[8] == " 8  r  n  b  k  q  b  n  r  8"


def test_last_move_squares_are_marked_in_the_grid():
    grid = board_grid(_fen_after(["e2e4"]), "e2e4")
    marked = {
        chess.square_name(cell.square)
        for row in grid.rows
        for cell in row
        if cell.is_last_from or cell.is_last_to
    }
    assert marked == {"e2", "e4"}


def test_no_last_move_marks_without_a_last_move():
    grid = board_grid(chess.STARTING_FEN)
    assert not any(cell.is_last_from or cell.is_last_to for row in grid.rows for cell in row)


def test_promotion_position_keeps_alignment():
    board = chess.Board("8/P7/8/8/8/8/7k/K7 w - - 0 1")
    board.push_uci("a7a8q")
    lines = board_lines(board_grid(board.fen(), "a7a8q"))
    assert lines[1] == " 8  Q  .  .  .  .  .  .  .  8"
    assert all(len(line) <= BOARD_WIDTH for line in lines)
