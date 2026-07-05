"""Thin wrapper around python-chess for move legality and application."""

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class MoveResult:
    legal: bool
    uci: str
    san: str | None
    fen_before: str
    fen_after: str
    is_check: bool
    is_checkmate: bool
    is_game_over: bool


def get_legal_moves(fen: str) -> list[str]:
    board = chess.Board(fen)
    return [move.uci() for move in board.legal_moves]


def apply_move(fen: str, uci: str) -> MoveResult:
    board = chess.Board(fen)

    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        move = None

    if move is None or move not in board.legal_moves:
        return MoveResult(
            legal=False,
            uci=uci,
            san=None,
            fen_before=fen,
            fen_after=fen,
            is_check=False,
            is_checkmate=False,
            is_game_over=False,
        )

    san = board.san(move)
    board.push(move)
    return MoveResult(
        legal=True,
        uci=uci,
        san=san,
        fen_before=fen,
        fen_after=board.fen(),
        is_check=board.is_check(),
        is_checkmate=board.is_checkmate(),
        is_game_over=board.is_game_over(),
    )
