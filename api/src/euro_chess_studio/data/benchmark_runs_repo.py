"""SQLite access for the benchmark_runs table. No business logic here;
the caller owns the transaction (the benchmark job handler runs inside
run_job's single transaction and must not commit)."""

import sqlite3
from datetime import UTC, datetime


def insert_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    suite_id: str,
    suite_content_hash: str,
    prompt_version: str,
    checkpoint: str,
    model: str,
    provider_alias: str | None,
    source: str,
    example_count: int,
    reply_count: int,
    transport_failed_count: int,
    position_set_id: str | None,
    job_config_id: str | None = None,
    note: str | None = None,
) -> sqlite3.Row:
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO benchmark_runs
            (id, suite_id, suite_content_hash, prompt_version, checkpoint,
             model, provider_alias, source, example_count, reply_count,
             transport_failed_count, position_set_id, job_config_id, note,
             created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            suite_id,
            suite_content_hash,
            prompt_version,
            checkpoint,
            model,
            provider_alias,
            source,
            example_count,
            reply_count,
            transport_failed_count,
            position_set_id,
            job_config_id,
            note,
            created_at,
        ),
    )
    row = get_run(conn, run_id)
    assert row is not None
    return row


def get_run(conn: sqlite3.Connection, run_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM benchmark_runs WHERE id = ?", (run_id,)).fetchone()


def list_runs(conn: sqlite3.Connection, *, suite_id: str | None = None) -> list[sqlite3.Row]:
    if suite_id is None:
        return conn.execute("SELECT * FROM benchmark_runs ORDER BY created_at").fetchall()
    return conn.execute(
        "SELECT * FROM benchmark_runs WHERE suite_id = ? ORDER BY created_at",
        (suite_id,),
    ).fetchall()
