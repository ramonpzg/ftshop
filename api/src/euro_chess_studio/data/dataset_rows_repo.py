"""SQLite access for the dataset_rows table. No business logic here."""

import json
import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_dataset_row(
    conn: sqlite3.Connection,
    *,
    workspace_id: str,
    move_id: str | None,
    shape: str,
    payload: dict,
) -> sqlite3.Row:
    row_id = generate_id("dsrow")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO dataset_rows (id, workspace_id, move_id, shape, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (row_id, workspace_id, move_id, shape, json.dumps(payload), created_at),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM dataset_rows WHERE id = ?", (row_id,)).fetchone()
    assert row is not None
    return row


def list_dataset_rows(conn: sqlite3.Connection, workspace_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM dataset_rows WHERE workspace_id = ? ORDER BY created_at",
        (workspace_id,),
    ).fetchall()


def list_dataset_rows_by_shape(conn: sqlite3.Connection, shape: str) -> list[sqlite3.Row]:
    """Every workspace's rows of one shape, oldest first. Used to export
    the room's combined training set."""
    return conn.execute(
        "SELECT * FROM dataset_rows WHERE shape = ? ORDER BY created_at",
        (shape,),
    ).fetchall()


def list_all_dataset_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """The whole room's rows, every shape, oldest first. Used for the
    instructor's full-archive export."""
    return conn.execute("SELECT * FROM dataset_rows ORDER BY created_at").fetchall()


def count_dataset_rows(conn: sqlite3.Connection) -> int:
    (count,) = conn.execute("SELECT COUNT(*) FROM dataset_rows").fetchone()
    return count


def delete_dataset_rows_for_workspace(conn: sqlite3.Connection, workspace_id: str) -> None:
    conn.execute("DELETE FROM dataset_rows WHERE workspace_id = ?", (workspace_id,))
    conn.commit()
