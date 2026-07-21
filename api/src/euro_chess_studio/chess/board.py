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


def get_playable_legal_moves(fen: str) -> list[str]:
    """Legal moves for a position that must be playable, not merely
    parseable. chess.Board() accepts FENs with a missing king, both
    sides in check, or pawns on the back rank, and happily generates
    moves for them; board.is_valid() is the gate that rejects those.
    Gameplay never needs this (its positions come from applying legal
    moves to the start position), but anything freezing external
    positions as evaluation data does. Raises ValueError either way."""
    board = chess.Board(fen)
    if not board.is_valid():
        raise ValueError(f"position is not playable: {board.status()!r}")
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
