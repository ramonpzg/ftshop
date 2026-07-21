"""SQLite access for the eval_suites table. No business logic here;
the caller owns the transaction."""

import json
import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_suite(
    conn: sqlite3.Connection,
    *,
    label: str,
    modality: str,
    origin: str,
    prompt_version: str,
    schema_version: str,
    example_count: int,
    content_hash: str,
    position_set_id: str,
    examples: list[dict],
    note: str | None = None,
) -> sqlite3.Row:
    suite_id = generate_id("suite")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO eval_suites
            (id, label, modality, origin, prompt_version, schema_version,
             example_count, content_hash, position_set_id, examples_json,
             note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            suite_id,
            label,
            modality,
            origin,
            prompt_version,
            schema_version,
            example_count,
            content_hash,
            position_set_id,
            json.dumps(examples),
            note,
            created_at,
        ),
    )
    row = get_suite(conn, suite_id)
    assert row is not None
    return row


def get_suite(conn: sqlite3.Connection, suite_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM eval_suites WHERE id = ?", (suite_id,)).fetchone()


def get_suite_by_content_hash(
    conn: sqlite3.Connection, modality: str, content_hash: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM eval_suites WHERE modality = ? AND content_hash = ?",
        (modality, content_hash),
    ).fetchone()


def list_suites(conn: sqlite3.Connection, *, modality: str | None = None) -> list[sqlite3.Row]:
    if modality is None:
        return conn.execute("SELECT * FROM eval_suites ORDER BY created_at").fetchall()
    return conn.execute(
        "SELECT * FROM eval_suites WHERE modality = ? ORDER BY created_at",
        (modality,),
    ).fetchall()
