"""Pure board rendering. Produces a cell grid and plain text lines; the
UI layer adds color on top of the same grid so styled and plain output
can never disagree on geometry.

Cells are four characters wide, and on a tall enough terminal each
rank gets a second, empty row under the pieces. Terminal glyphs are
roughly twice as tall as they are wide, so a 4x2 cell is the first
size that renders an actually square square. The single-row form
remains for cramped terminals; same grid, fewer rows.

    a   b   c   d   e   f   g   h
 8  r   n   b   q   k   b   n   r   8
 ...
 1  R   N   B   Q   K   B   N   R   1
    a   b   c   d   e   f   g   h

Uppercase is White, lowercase is Black, always, so the board stays
readable under a broken font, monochrome recording, or poor projector.
Every cell has a fixed width, so a check label or selection can never
shift the board."""

from dataclasses import dataclass

import chess

CELL = 4
BOARD_WIDTH = 3 + 8 * CELL + 2  # left label gutter, cells, right label
ROWS_SINGLE = 10
ROWS_TALL = 18


@dataclass(frozen=True)
class Cell:
    """One square, ready to render."""

    square: int
    piece: str  # "PNBRQK" / "pnbrqk" or "." for empty
    is_light: bool
    is_last_from: bool
    is_last_to: bool


@dataclass(frozen=True)
class BoardGrid:
    """Eight rows of eight cells, top row first, plus the labels the
    renderer needs. rank_labels[i] belongs to rows[i]."""

    rows: tuple[tuple[Cell, ...], ...]
    rank_labels: tuple[str, ...]
    file_labels: tuple[str, ...]


def board_grid(fen: str, last_move_uci: str | None = None, flipped: bool = False) -> BoardGrid:
    board = chess.Board(fen)
    last_from = last_to = -1
    if last_move_uci:
        move = chess.Move.from_uci(last_move_uci)
        last_from, last_to = move.from_square, move.to_square

    ranks = range(7, -1, -1) if not flipped else range(8)
    files = range(8) if not flipped else range(7, -1, -1)

    rows: list[tuple[Cell, ...]] = []
    for rank in ranks:
        row: list[Cell] = []
        for file in files:
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            row.append(
                Cell(
                    square=square,
                    piece=piece.symbol() if piece else ".",
                    is_light=bool((file + rank) % 2),
                    is_last_from=square == last_from,
                    is_last_to=square == last_to,
                )
            )
        rows.append(tuple(row))

    return BoardGrid(
        rows=tuple(rows),
        rank_labels=tuple(str(rank + 1) for rank in ranks),
        file_labels=tuple(chess.FILE_NAMES[file] for file in files),
    )


def board_lines(grid: BoardGrid, tall: bool = False) -> list[str]:
    """The plain text form: 10 lines single-height, 18 tall, each 37
    columns or less. In plain text the tall filler rows are blank; the
    styled renderer paints their square backgrounds. The styled
    renderer walks the same grid, so this is also the alignment
    contract the tests pin down."""
    file_row = ("   " + "".join(f" {label}  " for label in grid.file_labels)).rstrip()
    lines = [file_row]
    for label, row in zip(grid.rank_labels, grid.rows, strict=True):
        cells = "".join(f" {cell.piece}  " for cell in row)
        lines.append(f" {label} {cells} {label}")
        if tall:
            lines.append("")
    lines.append(file_row)
    return lines
