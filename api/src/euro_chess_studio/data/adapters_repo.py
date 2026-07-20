"""SQLite access for the adapters table. No business logic here; the
caller owns the transaction (the training job handler runs inside
run_job's single transaction and must not commit)."""

import json
import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_adapter(
    conn: sqlite3.Connection,
    *,
    label: str,
    modality: str,
    checkpoint: str,
    base_model: str,
    method: str,
    seed: int,
    output_task: str,
    config_id: str,
    config_hash: str,
    config: dict,
    dataset_snapshot_id: str,
    dataset_content_hash: str,
    runner: str,
    result_source: str,
    limitations: str,
) -> sqlite3.Row:
    adapter_id = generate_id("adapter")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO adapters
            (id, label, modality, checkpoint, base_model, method, seed,
             output_task, config_id, config_hash, config_json,
             dataset_snapshot_id, dataset_content_hash, runner,
             result_source, limitations, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            adapter_id,
            label,
            modality,
            checkpoint,
            base_model,
            method,
            seed,
            output_task,
            config_id,
            config_hash,
            json.dumps(config),
            dataset_snapshot_id,
            dataset_content_hash,
            runner,
            result_source,
            limitations,
            created_at,
        ),
    )
    row = get_adapter(conn, adapter_id)
    assert row is not None
    return row


def get_adapter(conn: sqlite3.Connection, adapter_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM adapters WHERE id = ?", (adapter_id,)).fetchone()


def get_adapter_by_checkpoint(
    conn: sqlite3.Connection, modality: str, checkpoint: str
) -> sqlite3.Row | None:
    """Newest first: re-training the same checkpoint label against a
    different snapshot or config produces a new row, and consumers that
    resolve a checkpoint want the current one."""
    return conn.execute(
        "SELECT * FROM adapters WHERE modality = ? AND checkpoint = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (modality, checkpoint),
    ).fetchone()


def find_adapter(
    conn: sqlite3.Connection,
    *,
    modality: str,
    checkpoint: str,
    config_hash: str,
    dataset_content_hash: str,
) -> sqlite3.Row | None:
    """The exact-identity lookup the training replay uses: the same
    config over the same frozen dataset is the same adapter, so a rerun
    returns the existing row instead of minting a duplicate."""
    return conn.execute(
        "SELECT * FROM adapters WHERE modality = ? AND checkpoint = ? "
        "AND config_hash = ? AND dataset_content_hash = ?",
        (modality, checkpoint, config_hash, dataset_content_hash),
    ).fetchone()


def list_adapters(conn: sqlite3.Connection, *, modality: str | None = None) -> list[sqlite3.Row]:
    if modality is None:
        return conn.execute("SELECT * FROM adapters ORDER BY created_at").fetchall()
    return conn.execute(
        "SELECT * FROM adapters WHERE modality = ? ORDER BY created_at",
        (modality,),
    ).fetchall()
