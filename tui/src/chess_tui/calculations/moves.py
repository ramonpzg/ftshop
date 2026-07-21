"""Pure participant-move parsing. python-chess is the only authority on
legality; this module just translates a typed line into its verdict."""

import re
from dataclasses import dataclass
from typing import Literal

import chess

_UCI_SHAPE = re.compile(r"^[a-h][1-8][a-h][1-8][nbrqNBRQ]?$")


@dataclass(frozen=True)
class ParsedMove:
    uci: str
    san: str


@dataclass(frozen=True)
class MoveRejection:
    kind: Literal["illegal", "ambiguous", "unrecognized"]
    detail: str


def parse_participant_move(fen: str, text: str) -> ParsedMove | MoveRejection:
    """UCI first, SAN second. Promotion works in both spellings
    (e7e8q, e8=Q). Phone keyboards auto-capitalize, so UCI is matched
    case-insensitively and a pawn SAN like "E4" gets one lowercased
    retry. Rejections carry a terse reason for the state line."""
    board = chess.Board(fen)
    raw = text.strip()

    if _UCI_SHAPE.match(raw.lower()):
        move = chess.Move.from_uci(raw.lower())
        if move in board.legal_moves:
            return ParsedMove(uci=move.uci(), san=board.san(move))
        promoted = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)
        if move.promotion is None and promoted in board.legal_moves:
            uci = move.uci()
            return MoveRejection("illegal", f"{uci} needs a promotion piece, like {uci}q")
        return MoveRejection("illegal", f"illegal move: {raw}")

    for candidate in _san_candidates(raw):
        try:
            move = board.parse_san(candidate)
        except chess.AmbiguousMoveError:
            return MoveRejection("ambiguous", f"ambiguous: {raw}. add a file or rank, like Nbd2")
        except chess.IllegalMoveError:
            return MoveRejection("illegal", f"illegal move: {raw}")
        except (chess.InvalidMoveError, ValueError):
            continue
        return ParsedMove(uci=move.uci(), san=board.san(move))
    return MoveRejection("unrecognized", f"not a move or command: {raw}. try help")


def _san_candidates(raw: str) -> list[str]:
    candidates = [raw]
    if raw[:1] in "ABCDEFGH":
        candidates.append(raw[0].lower() + raw[1:])
    return candidates


def san_history_text(sans: list[str]) -> str:
    """Compact numbered SAN history: "1. e4 e5 2. Nf3". "-" when empty,
    the shape the model prompt documents."""
    if not sans:
        return "-"
    parts: list[str] = []
    for index, san in enumerate(sans):
        if index % 2 == 0:
            parts.append(f"{index // 2 + 1}. {san}")
        else:
            parts.append(san)
    return " ".join(parts)


def legal_moves_uci_san(fen: str) -> list[tuple[str, str]]:
    """Every legal move as (uci, san), sorted by UCI so the prompt is
    deterministic for a given position."""
    board = chess.Board(fen)
    moves = sorted(board.legal_moves, key=lambda m: m.uci())
    return [(m.uci(), board.san(m)) for m in moves]
