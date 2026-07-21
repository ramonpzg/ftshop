"""History listing and replay. Replay renders stored positions and the
recorded comments; it is evidence of what happened, not analysis. No
move is ever labelled a mistake here because nothing evaluates moves."""

import sqlite3
from dataclasses import dataclass

import chess

from chess_tui.data import games_repo, plies_repo


@dataclass(frozen=True)
class HistoryItem:
    game_id: str
    started_at: str
    result: str | None
    termination: str | None
    move_count: int


@dataclass(frozen=True)
class ReplayPly:
    ply: int
    actor: str
    uci: str
    san: str
    fen_after: str
    comment: str | None


@dataclass
class ReplayCursor:
    """index 0 is the starting position; index n is after ply n."""

    game_id: str
    started_at: str
    result: str | None
    termination: str | None
    plies: list[ReplayPly]
    index: int = 0

    @property
    def fen(self) -> str:
        if self.index == 0:
            return chess.STARTING_FEN
        return self.plies[self.index - 1].fen_after

    @property
    def current(self) -> ReplayPly | None:
        if self.index == 0:
            return None
        return self.plies[self.index - 1]

    def forward(self) -> None:
        if self.index < len(self.plies):
            self.index += 1

    def back(self) -> None:
        if self.index > 0:
            self.index -= 1


def list_history(conn: sqlite3.Connection) -> list[HistoryItem]:
    items = []
    for row in games_repo.list_games_newest_first(conn):
        items.append(
            HistoryItem(
                game_id=row["id"],
                started_at=row["started_at"],
                result=row["result"],
                termination=row["termination"],
                move_count=(int(row["ply_count"]) + 1) // 2,
            )
        )
    return items


def open_replay(conn: sqlite3.Connection, game_id: str) -> ReplayCursor | None:
    game = games_repo.get_game(conn, game_id)
    if game is None:
        return None
    plies = [
        ReplayPly(
            ply=row["ply"],
            actor=row["actor"],
            uci=row["uci"],
            san=row["san"],
            fen_after=row["fen_after"],
            comment=row["comment"],
        )
        for row in plies_repo.plies_for_game(conn, game_id)
    ]
    return ReplayCursor(
        game_id=game_id,
        started_at=game["started_at"],
        result=game["result"],
        termination=game["termination"],
        plies=plies,
    )
