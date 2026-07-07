"""Actions for the timed-game lifecycle: start, start over, timeout.

The rules, stated once: a match runs on one clock (default five
minutes, thirty max). Starting over ends the current game as a loss.
Letting the clock run out is a loss. The only free way out of a match
is winning it, which is the point.
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

import chess

from euro_chess_studio.actions.errors import (
    GameAlreadyActiveError,
    GameNotExpiredError,
    InvalidTimeLimitError,
    NoActiveGameError,
    WorkspaceNotFoundError,
)
from euro_chess_studio.calculations.game_clock import (
    is_expired,
    is_valid_time_limit,
    summarize_results,
)
from euro_chess_studio.data.dataset_rows_repo import count_dataset_rows
from euro_chess_studio.data.games_repo import (
    end_game,
    get_active_game,
    insert_game,
    list_active_games,
    list_finished_games,
    list_games_with_details,
)
from euro_chess_studio.data.workspaces_repo import get_workspace, update_board_fen


@dataclass(frozen=True)
class GameStatus:
    workspace: sqlite3.Row
    game: sqlite3.Row | None
    record: dict
    history: list[sqlite3.Row]
    # True when this very read converted a stale game into a timeout
    # loss: the player was away and deserves to be told what happened.
    expired_while_away: bool = False


def expire_if_over(conn: sqlite3.Connection, game: sqlite3.Row | None) -> sqlite3.Row | None:
    """Reconciles an active game with the wall clock. Returns the still
    active game, or None once it has been marked a timeout loss. Called
    on every read so a reload after lunch shows the loss it earned."""
    if game is None or game["result"] is not None:
        return None if game is None else game
    if is_expired(game["started_at"], game["time_limit_seconds"], datetime.now(UTC)):
        end_game(conn, game["id"], "loss_timeout")
        return None
    return game


def _require_workspace(conn: sqlite3.Connection, workspace_id: str) -> sqlite3.Row:
    workspace = get_workspace(conn, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError(f"unknown workspace id: {workspace_id}")
    return workspace


def _status(
    conn: sqlite3.Connection,
    workspace_id: str,
    game: sqlite3.Row | None,
    expired_while_away: bool = False,
) -> GameStatus:
    workspace = _require_workspace(conn, workspace_id)
    history = list_finished_games(conn, workspace_id)
    record = summarize_results(row["result"] for row in history)
    return GameStatus(
        workspace=workspace,
        game=game,
        record=record,
        history=history,
        expired_while_away=expired_while_away,
    )


def game_status(conn: sqlite3.Connection, workspace_id: str) -> GameStatus:
    _require_workspace(conn, workspace_id)
    active = get_active_game(conn, workspace_id)
    game = expire_if_over(conn, active)
    expired_while_away = active is not None and game is None
    return _status(conn, workspace_id, game, expired_while_away=expired_while_away)


def start_game(conn: sqlite3.Connection, workspace_id: str, time_limit_seconds: int) -> GameStatus:
    """Begins a fresh timed match from the starting position."""
    _require_workspace(conn, workspace_id)
    if not is_valid_time_limit(time_limit_seconds):
        raise InvalidTimeLimitError(
            f"time limit must be 60 to 1800 seconds, got {time_limit_seconds}"
        )
    if expire_if_over(conn, get_active_game(conn, workspace_id)) is not None:
        raise GameAlreadyActiveError("a game is already running; start over to leave it")

    game = insert_game(conn, workspace_id=workspace_id, time_limit_seconds=time_limit_seconds)
    update_board_fen(conn, workspace_id, chess.STARTING_FEN)
    return _status(conn, workspace_id, game)


def start_over(conn: sqlite3.Connection, workspace_id: str) -> GameStatus:
    """The Duolingo rule: quitting mid-game is a loss, recorded before
    the fresh board appears. If the clock already ran out, the loss is
    a timeout, not a resignation; either way it counts."""
    _require_workspace(conn, workspace_id)
    active = get_active_game(conn, workspace_id)
    if active is None:
        raise NoActiveGameError("no game to start over; start one first")

    if expire_if_over(conn, active) is not None:
        end_game(conn, active["id"], "loss_resign")

    game = insert_game(
        conn, workspace_id=workspace_id, time_limit_seconds=active["time_limit_seconds"]
    )
    update_board_fen(conn, workspace_id, chess.STARTING_FEN)
    return _status(conn, workspace_id, game)


@dataclass(frozen=True)
class RoomGames:
    games: list[sqlite3.Row]
    total_dataset_rows: int


def room_games(conn: sqlite3.Connection) -> RoomGames:
    """Every game in the room for the presenter dashboard. Reconciles
    all active clocks with the wall clock first, so a game that died
    while its player was at the coffee machine shows as the loss it
    is, not as forever 'playing'."""
    for active in list_active_games(conn):
        expire_if_over(conn, active)
    return RoomGames(
        games=list_games_with_details(conn),
        total_dataset_rows=count_dataset_rows(conn),
    )


def flag_timeout(conn: sqlite3.Connection, workspace_id: str) -> GameStatus:
    """The client's clock hit zero. The server checks its own before
    recording the loss; a client cannot flag a game early."""
    _require_workspace(conn, workspace_id)
    active = get_active_game(conn, workspace_id)
    if active is None:
        raise NoActiveGameError("no game to flag")
    if expire_if_over(conn, active) is not None:
        raise GameNotExpiredError("the clock has not run out yet")
    return _status(conn, workspace_id, None)
