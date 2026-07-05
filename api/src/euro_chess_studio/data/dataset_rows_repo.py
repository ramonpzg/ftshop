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
