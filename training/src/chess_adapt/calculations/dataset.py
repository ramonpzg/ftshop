"""Pure chess selection and SFT row construction.

The source corpus is large enough to be a trap. Selection is therefore
bounded by one pinned Parquet file, a scan limit, and an output limit.
No source usernames are copied into the processed sample.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from typing import Any

import chess
import chess.pgn
from euro_chess_studio.calculations.export import PROMPT_TEMPLATE, SFT_PROMPT_VERSION
from euro_chess_studio.calculations.llm_prompts import ASSESS_SYSTEM_PROMPT

SELECTED_GAME_SCHEMA = "lichess-low-capture-game-v1"
ENRICHMENT_SCHEMA = "chess-real-world-enrichment-v2"
SFT_SCHEMA = "gemma-chat-sft-v1"

REAL_WORLD_DOMAINS = (
    "a software release or incident response",
    "a hospital team coordinating urgent care",
    "conference or event logistics",
    "a restaurant kitchen during service",
    "airport or rail operations",
    "a construction or repair crew",
    "a live performance backstage",
    "scientific fieldwork or a laboratory procedure",
    "a small business negotiation",
    "a classroom or group project",
    "a film crew solving a production problem",
    "a community sports practice",
)


@dataclass(frozen=True)
class SelectionConfig:
    limit: int = 64
    scan_limit: int = 121_332
    max_plies: int = 60
    max_winner_captures: int = 3
    split_seed: int = 2026

    def validate(self) -> None:
        if self.limit < 1:
            raise ValueError("limit must be positive")
        if self.scan_limit < self.limit:
            raise ValueError("scan_limit must be at least limit")
        if self.max_plies < 2:
            raise ValueError("max_plies must be at least 2")
        if self.max_winner_captures < 0:
            raise ValueError("max_winner_captures cannot be negative")


def select_game(row: dict[str, Any], config: SelectionConfig) -> dict[str, Any] | None:
    """Return one checked, anonymised game or ``None`` when it misses the filter."""
    config.validate()
    result = row.get("Result")
    if result not in {"1-0", "0-1"} or row.get("Termination") != "Normal":
        return None
    movetext = row.get("movetext")
    site = row.get("Site")
    if not isinstance(movetext, str) or not isinstance(site, str):
        return None

    game = _parse_game(movetext, result)
    if game is None:
        return None

    board = game.board()
    winner = chess.WHITE if result == "1-0" else chess.BLACK
    san_moves: list[str] = []
    uci_moves: list[str] = []
    winner_captures: list[str] = []
    loser_captures: list[str] = []
    for move in game.mainline_moves():
        if move not in board.legal_moves:
            return None
        san_moves.append(board.san(move))
        uci_moves.append(move.uci())
        if board.is_capture(move):
            captured = _captured_piece_name(board, move)
            target = winner_captures if board.turn == winner else loser_captures
            target.append(captured)
        board.push(move)

    if not board.is_checkmate():
        return None
    if len(uci_moves) > config.max_plies:
        return None
    if len(winner_captures) > config.max_winner_captures:
        return None

    game_id = hashlib.sha256(site.encode()).hexdigest()[:16]
    return {
        "schema_version": SELECTED_GAME_SCHEMA,
        "game_id": game_id,
        "source_site": site,
        "event": _optional_text(row.get("Event")),
        "played_at": _played_at(row),
        "result": result,
        "winner": "white" if winner == chess.WHITE else "black",
        "white_elo": _optional_int(row.get("WhiteElo")),
        "black_elo": _optional_int(row.get("BlackElo")),
        "eco": _optional_text(row.get("ECO")),
        "opening": _optional_text(row.get("Opening")),
        "time_control": _optional_text(row.get("TimeControl")),
        "movetext": movetext,
        "san_moves": san_moves,
        "uci_moves": uci_moves,
        "final_fen": board.fen(),
        "ply_count": len(uci_moves),
        "fullmove_count": (len(uci_moves) + 1) // 2,
        "winner_capture_count": len(winner_captures),
        "winner_captured_pieces": winner_captures,
        "loser_capture_count": len(loser_captures),
        "loser_captured_pieces": loser_captures,
    }


def build_enrichment_messages(game: dict[str, Any]) -> list[dict[str, str]]:
    """A complete-game prompt for Luna's real-world mapping and video scene."""
    domain = domain_for_game(game["game_id"])
    user = (
        f"Complete game (SAN): {' '.join(game['san_moves'])}\n"
        f"Result: {game['result']} by checkmate in {game['fullmove_count']} moves.\n"
        f"The winner captured {game['winner_capture_count']} pieces: "
        f"{', '.join(game['winner_captured_pieces']) or 'none'}.\n"
        f"Final position (FEN): {game['final_fen']}\n\n"
        "Explain what made this low-capture win work, relate its sequence and trade-offs "
        "to one concrete real-world situation, then write a detailed short-video prompt "
        "showing only that real-world situation. Keep the relationship specific to this game.\n"
        f"Assigned setting: {domain}. Use that setting rather than a generic security, "
        "intruder, guard, warehouse, or corridor scene.\n"
        'Respond with JSON: {"assessment": "...", "real_world": "...", '
        '"video_prompt": "..."}'
    )
    return [
        {"role": "system", "content": ASSESS_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def build_sft_rows(
    games: list[dict[str, Any]],
    enrichments: dict[str, dict[str, Any]],
    *,
    split_seed: int,
) -> list[dict[str, Any]]:
    """Build move-choice and real-world mapping rows with game-level splits."""
    rows: list[dict[str, Any]] = []
    for game in games:
        split = split_for_game(game["game_id"], split_seed)
        board = chess.Board()
        winner = chess.WHITE if game["winner"] == "white" else chess.BLACK
        for ply, uci in enumerate(game["uci_moves"]):
            move = chess.Move.from_uci(uci)
            if board.turn == winner:
                legal_moves = sorted(candidate.uci() for candidate in board.legal_moves)
                prompt = PROMPT_TEMPLATE.format(fen=board.fen(), legal_moves=", ".join(legal_moves))
                rows.append(
                    {
                        "schema_version": SFT_SCHEMA,
                        "row_id": f"{game['game_id']}:move:{ply}",
                        "game_id": game["game_id"],
                        "task": "move",
                        "split": split,
                        "fen": board.fen(),
                        "legal_moves": legal_moves,
                        "target_uci": uci,
                        "messages": [
                            {"role": "user", "content": prompt},
                            {
                                "role": "assistant",
                                "content": json.dumps({"move": uci}, separators=(",", ":")),
                            },
                        ],
                        "prompt_version": SFT_PROMPT_VERSION,
                    }
                )
            board.push(move)

        enrichment = enrichments.get(game["game_id"])
        if (
            enrichment
            and enrichment.get("status") == "succeeded"
            and enrichment.get("schema_version") == ENRICHMENT_SCHEMA
        ):
            answer = {
                "assessment": enrichment["assessment"],
                "real_world": enrichment["real_world"],
                "video_prompt": enrichment["video_prompt"],
            }
            rows.append(
                {
                    "schema_version": SFT_SCHEMA,
                    "row_id": f"{game['game_id']}:scenario",
                    "game_id": game["game_id"],
                    "task": "scenario",
                    "split": split,
                    "messages": [
                        *build_enrichment_messages(game),
                        {
                            "role": "assistant",
                            "content": json.dumps(answer, separators=(",", ":")),
                        },
                    ],
                    "prompt_version": "assess-complete-game-v2",
                }
            )
    return rows


def split_for_game(game_id: str, seed: int) -> str:
    bucket = int(hashlib.sha256(f"{seed}:{game_id}".encode()).hexdigest()[:8], 16) % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "validation"
    return "test"


def domain_for_game(game_id: str) -> str:
    bucket = int(hashlib.sha256(f"domain:{game_id}".encode()).hexdigest()[:8], 16)
    return REAL_WORLD_DOMAINS[bucket % len(REAL_WORLD_DOMAINS)]


def content_hash(rows: list[dict[str, Any]]) -> str:
    lines = [json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows]
    return hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()


def _parse_game(movetext: str, result: str) -> chess.pgn.Game | None:
    source = f'[Result "{result}"]\n\n{movetext}'
    try:
        game = chess.pgn.read_game(io.StringIO(source))
    except (ValueError, UnicodeError):
        return None
    if game is None or game.errors:
        return None
    return game


def _captured_piece_name(board: chess.Board, move: chess.Move) -> str:
    if board.is_en_passant(move):
        return "pawn"
    piece = board.piece_at(move.to_square)
    return chess.piece_name(piece.piece_type) if piece else "unknown"


def _played_at(row: dict[str, Any]) -> str | None:
    date = row.get("UTCDate")
    time = row.get("UTCTime")
    if date is None:
        return None
    return f"{date.isoformat()}T{time.isoformat() if time is not None else '00:00:00'}Z"


def _optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) else None
