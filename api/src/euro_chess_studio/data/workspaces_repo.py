"""SQLite access for the workspaces table. No business logic here."""

import sqlite3
from datetime import UTC, datetime


def count_workspaces_for_page(conn: sqlite3.Connection, page_id: str) -> int:
    (count,) = conn.execute(
        "SELECT COUNT(*) FROM workspaces WHERE page_id = ?", (page_id,)
    ).fetchone()
    return count


def get_workspace_for_user_and_page(
    conn: sqlite3.Connection, user_id: str, page_id: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM workspaces WHERE user_id = ? AND page_id = ?", (user_id, page_id)
    ).fetchone()


def insert_workspace(
    conn: sqlite3.Connection,
    workspace_id: str,
    user_id: str,
    page_id: str,
    shape_id: str,
    board_fen: str,
) -> sqlite3.Row:
    # position_index is allocated inside the INSERT so two simultaneous
    # joins can never read the same count and stack their workspaces on
    # top of each other. A single statement is atomic in SQLite.
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO workspaces
            (id, user_id, page_id, shape_id, position_index, board_fen, created_at)
        VALUES (?, ?, ?, ?,
                (SELECT COUNT(*) FROM workspaces WHERE page_id = ?),
                ?, ?)
        """,
        (workspace_id, user_id, page_id, shape_id, page_id, board_fen, created_at),
    )
    conn.commit()
    row = get_workspace(conn, workspace_id)
    assert row is not None
    return row


def get_workspace(conn: sqlite3.Connection, workspace_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()


def list_workspaces(conn: sqlite3.Connection, page_id: str | None = None) -> list[sqlite3.Row]:
    if page_id is not None:
        return conn.execute(
            "SELECT * FROM workspaces WHERE page_id = ? ORDER BY position_index", (page_id,)
        ).fetchall()
    return conn.execute("SELECT * FROM workspaces ORDER BY created_at").fetchall()


def list_workspaces_with_details(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Workspaces joined with their user name and page slug/title, for the attendee panel."""
    return conn.execute(
        """
        SELECT
            workspaces.*,
            users.name AS user_name,
            pages.slug AS page_slug,
            pages.title AS page_title
        FROM workspaces
        JOIN users ON users.id = workspaces.user_id
        JOIN pages ON pages.id = workspaces.page_id
        ORDER BY workspaces.created_at
        """
    ).fetchall()


def update_board_fen(conn: sqlite3.Connection, workspace_id: str, board_fen: str) -> None:
    conn.execute("UPDATE workspaces SET board_fen = ? WHERE id = ?", (board_fen, workspace_id))
    conn.commit()


def update_selected_snippet(conn: sqlite3.Connection, workspace_id: str, snippet_id: str) -> None:
    conn.execute(
        "UPDATE workspaces SET selected_snippet_id = ? WHERE id = ?", (snippet_id, workspace_id)
    )
    conn.commit()
