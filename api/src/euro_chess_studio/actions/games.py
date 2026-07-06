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
from euro_chess_studio.data.games_repo import (
    end_game,
    get_active_game,
    insert_game,
    list_finished_results,
)
from euro_chess_studio.data.workspaces_repo import get_workspace, update_board_fen


@dataclass(frozen=True)
class GameStatus:
    workspace: sqlite3.Row
    game: sqlite3.Row | None
    record: dict


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


def _status(conn: sqlite3.Connection, workspace_id: str, game: sqlite3.Row | None) -> GameStatus:
    workspace = _require_workspace(conn, workspace_id)
    record = summarize_results(list_finished_results(conn, workspace_id))
    return GameStatus(workspace=workspace, game=game, record=record)


def game_status(conn: sqlite3.Connection, workspace_id: str) -> GameStatus:
    _require_workspace(conn, workspace_id)
    game = expire_if_over(conn, get_active_game(conn, workspace_id))
    return _status(conn, workspace_id, game)


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
