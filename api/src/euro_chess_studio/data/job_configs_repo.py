"""SQLite access for the job_configs table. No business logic here;
the caller owns the transaction."""

import json
import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_job_config(
    conn: sqlite3.Connection,
    *,
    workspace_id: str | None,
    job_type: str,
    params: dict,
    job_config_id: str | None = None,
) -> sqlite3.Row:
    """job_config_id lets run_job hand the id to a handler before this
    row exists (the row lands later in the same transaction); omitted,
    one is generated here."""
    job_config_id = job_config_id or generate_id("job")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO job_configs (id, workspace_id, job_type, params_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (job_config_id, workspace_id, job_type, json.dumps(params), created_at),
    )
    row = conn.execute("SELECT * FROM job_configs WHERE id = ?", (job_config_id,)).fetchone()
    assert row is not None
    return row
