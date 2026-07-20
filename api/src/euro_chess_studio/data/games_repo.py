"""SQLite access for the games table. No business logic here."""

import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_game(
    conn: sqlite3.Connection,
    *,
    workspace_id: str,
    time_limit_seconds: int,
    started_at: str | None = None,
    opponent_model: str | None = None,
) -> sqlite3.Row:
    game_id = generate_id("game")
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO games
            (id, workspace_id, time_limit_seconds, opponent_model, started_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (game_id, workspace_id, time_limit_seconds, opponent_model, started_at or now, now),
    )
    row = get_game(conn, game_id)
    assert row is not None
    return row


def get_game(conn: sqlite3.Connection, game_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()


def get_active_game(conn: sqlite3.Connection, workspace_id: str) -> sqlite3.Row | None:
    """The one unfinished game for a workspace, if any."""
    return conn.execute(
        "SELECT * FROM games WHERE workspace_id = ? AND result IS NULL ORDER BY created_at DESC",
        (workspace_id,),
    ).fetchone()


def end_game(conn: sqlite3.Connection, game_id: str, result: str) -> sqlite3.Row:
    ended_at = datetime.now(UTC).isoformat()
    conn.execute(
        "UPDATE games SET result = ?, ended_at = ? WHERE id = ?", (result, ended_at, game_id)
    )
    row = get_game(conn, game_id)
    assert row is not None
    return row


def list_finished_games(conn: sqlite3.Connection, workspace_id: str) -> list[sqlite3.Row]:
    """Finished games, newest first, each with its legal move count."""
    return conn.execute(
        """
        SELECT games.*,
               (SELECT COUNT(*) FROM moves
                WHERE moves.game_id = games.id AND moves.is_legal = 1) AS legal_moves
        FROM games
        WHERE workspace_id = ? AND result IS NOT NULL
        ORDER BY ended_at DESC, created_at DESC
        """,
        (workspace_id,),
    ).fetchall()


def list_games_with_details(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every game in the room, active first, with the player's name and
    per-game move and dataset-row counts. Feeds the presenter dashboard."""
    return conn.execute(
        """
        SELECT games.*,
               users.name AS user_name,
               (SELECT COUNT(*) FROM moves
                WHERE moves.game_id = games.id AND moves.is_legal = 1) AS legal_moves,
               (SELECT COUNT(*) FROM dataset_rows
                JOIN moves ON moves.id = dataset_rows.move_id
                WHERE moves.game_id = games.id) AS dataset_rows
        FROM games
        JOIN workspaces ON workspaces.id = games.workspace_id
        JOIN users ON users.id = workspaces.user_id
        ORDER BY (games.result IS NULL) DESC, games.started_at DESC
        """
    ).fetchall()


def list_active_games(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM games WHERE result IS NULL").fetchall()


def delete_games_for_workspace(conn: sqlite3.Connection, workspace_id: str) -> None:
    conn.execute("DELETE FROM games WHERE workspace_id = ?", (workspace_id,))
