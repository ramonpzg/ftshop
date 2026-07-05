"""SQLite access for the artifacts table. No business logic here."""

import json
import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_artifact(
    conn: sqlite3.Connection,
    *,
    job_config_id: str | None,
    modality: str,
    kind: str,
    payload: dict,
    cached: bool,
) -> sqlite3.Row:
    artifact_id = generate_id("artifact")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO artifacts (id, job_config_id, modality, kind, payload_json, cached, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (artifact_id, job_config_id, modality, kind, json.dumps(payload), int(cached), created_at),
    )
    conn.commit()
    row = get_artifact(conn, artifact_id)
    assert row is not None
    return row


def get_artifact(conn: sqlite3.Connection, artifact_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()


def list_artifacts(conn: sqlite3.Connection, modality: str | None = None) -> list[sqlite3.Row]:
    if modality is not None:
        return conn.execute(
            "SELECT * FROM artifacts WHERE modality = ? ORDER BY created_at DESC", (modality,)
        ).fetchall()
    return conn.execute("SELECT * FROM artifacts ORDER BY created_at DESC").fetchall()
