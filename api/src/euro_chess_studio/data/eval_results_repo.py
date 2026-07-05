"""SQLite access for the eval_results table. No business logic here."""

import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_eval_result(
    conn: sqlite3.Connection,
    *,
    modality: str,
    metric: str,
    value: float,
    workspace_id: str | None,
    source: str,
) -> sqlite3.Row:
    result_id = generate_id("eval")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO eval_results (id, modality, metric, value, workspace_id, source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (result_id, modality, metric, value, workspace_id, source, created_at),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM eval_results WHERE id = ?", (result_id,)).fetchone()
    assert row is not None
    return row


def list_eval_results(
    conn: sqlite3.Connection,
    *,
    modality: str | None = None,
    workspace_id: str | None = None,
) -> list[sqlite3.Row]:
    query = "SELECT * FROM eval_results WHERE 1 = 1"
    params: list[str] = []
    if modality is not None:
        query += " AND modality = ?"
        params.append(modality)
    if workspace_id is not None:
        query += " AND workspace_id = ?"
        params.append(workspace_id)
    query += " ORDER BY created_at"
    return conn.execute(query, params).fetchall()
