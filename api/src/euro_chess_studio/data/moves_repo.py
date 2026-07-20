"""SQLite access for the moves table. No business logic here."""

import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def count_legal_moves(conn: sqlite3.Connection, workspace_id: str) -> int:
    (count,) = conn.execute(
        "SELECT COUNT(*) FROM moves WHERE workspace_id = ? AND is_legal = 1", (workspace_id,)
    ).fetchone()
    return count


def insert_move(
    conn: sqlite3.Connection,
    *,
    workspace_id: str,
    uci: str,
    san: str | None,
    fen_before: str,
    fen_after: str,
    is_legal: bool,
    is_check: bool,
    is_checkmate: bool,
    reward: int,
    actor: str,
    model: str | None = None,
    game_id: str | None = None,
) -> sqlite3.Row:
    # ply is allocated inside the INSERT (count of legal moves so far)
    # so two in-flight requests can never claim the same ply. It is
    # scoped to the game (IS handles the NULL of free play) so a fresh
    # match starts its PGN at move one instead of inheriting history.
    # The caller owns the transaction; no commit here.
    move_id = generate_id("move")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO moves
            (id, workspace_id, game_id, ply, uci, san, fen_before, fen_after,
             is_legal, is_check, is_checkmate, reward, actor, model, created_at)
        VALUES (?, ?, ?,
                (SELECT COUNT(*) FROM moves
                 WHERE workspace_id = ? AND is_legal = 1 AND game_id IS ?),
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            move_id,
            workspace_id,
            game_id,
            workspace_id,
            game_id,
            uci,
            san,
            fen_before,
            fen_after,
            int(is_legal),
            int(is_check),
            int(is_checkmate),
            reward,
            actor,
            model,
            created_at,
        ),
    )
    row = get_move(conn, move_id)
    assert row is not None
    return row


def get_move(conn: sqlite3.Connection, move_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM moves WHERE id = ?", (move_id,)).fetchone()


def list_moves(conn: sqlite3.Connection, workspace_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM moves WHERE workspace_id = ? ORDER BY ply, created_at", (workspace_id,)
    ).fetchall()


def list_legal_sans(
    conn: sqlite3.Connection, workspace_id: str, game_id: str | None = None
) -> list[str]:
    """Legal SANs in order, scoped to one game (or to free play when
    game_id is None) so PGN prefixes never leak across matches."""
    rows = conn.execute(
        """
        SELECT san FROM moves
        WHERE workspace_id = ? AND is_legal = 1 AND game_id IS ?
        ORDER BY ply, created_at
        """,
        (workspace_id, game_id),
    ).fetchall()
    return [row["san"] for row in rows]


def list_moves_by_actor(
    conn: sqlite3.Connection, workspace_id: str, actor: str
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM moves WHERE workspace_id = ? AND actor = ? ORDER BY ply, created_at",
        (workspace_id, actor),
    ).fetchall()


def delete_moves_for_workspace(conn: sqlite3.Connection, workspace_id: str) -> None:
    conn.execute("DELETE FROM moves WHERE workspace_id = ?", (workspace_id,))
