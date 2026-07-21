"""SQLite access for the dataset_snapshots table. No business logic
here; the caller owns the transaction."""

import json
import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_snapshot(
    conn: sqlite3.Connection,
    *,
    label: str,
    modality: str,
    origin: str,
    schema_version: str,
    row_count: int,
    excluded_ineligible_count: int,
    source_game_count: int,
    source_workspace_count: int,
    scenario_raw_count: int,
    scenario_approved_count: int,
    content_hash: str,
    rows: list[dict],
    source_row_ids: list[str],
    note: str | None = None,
) -> sqlite3.Row:
    snapshot_id = generate_id("snapshot")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO dataset_snapshots
            (id, label, modality, origin, schema_version, row_count,
             excluded_ineligible_count, source_game_count, source_workspace_count,
             scenario_raw_count, scenario_approved_count, content_hash,
             rows_json, source_row_ids_json, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id,
            label,
            modality,
            origin,
            schema_version,
            row_count,
            excluded_ineligible_count,
            source_game_count,
            source_workspace_count,
            scenario_raw_count,
            scenario_approved_count,
            content_hash,
            json.dumps(rows),
            json.dumps(source_row_ids),
            note,
            created_at,
        ),
    )
    row = get_snapshot(conn, snapshot_id)
    assert row is not None
    return row


def get_snapshot(conn: sqlite3.Connection, snapshot_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM dataset_snapshots WHERE id = ?", (snapshot_id,)).fetchone()


def get_snapshot_by_content_hash(
    conn: sqlite3.Connection, modality: str, content_hash: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM dataset_snapshots WHERE modality = ? AND content_hash = ?",
        (modality, content_hash),
    ).fetchone()


def list_snapshots(conn: sqlite3.Connection, *, modality: str | None = None) -> list[sqlite3.Row]:
    if modality is None:
        return conn.execute("SELECT * FROM dataset_snapshots ORDER BY created_at").fetchall()
    return conn.execute(
        "SELECT * FROM dataset_snapshots WHERE modality = ? ORDER BY created_at",
        (modality,),
    ).fetchall()
