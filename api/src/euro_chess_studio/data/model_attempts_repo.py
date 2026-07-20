"""SQLite access for the model_attempts table. No business logic here.
Rows are immutable once written; the caller owns the transaction."""

import json
import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_attempt(
    conn: sqlite3.Connection,
    *,
    workspace_id: str | None,
    task: str,
    actor: str,
    attempt_number: int,
    status: str,
    game_id: str | None = None,
    model: str | None = None,
    provider_alias: str | None = None,
    prompt_version: str | None = None,
    checkpoint: str | None = None,
    ply: int | None = None,
    fen: str | None = None,
    raw_response: str | None = None,
    request_ids: tuple[str, ...] = (),
    json_requested: bool = False,
    parse_ok: bool = False,
    parsed_move: str | None = None,
    is_legal: bool | None = None,
    applied_move_id: str | None = None,
    error_detail: str | None = None,
    transport_attempts: int | None = None,
    json_mode_dropped: bool | None = None,
    reasoning_effort_dropped: bool | None = None,
    reply_source: str = "live",
    benchmark_run_id: str | None = None,
    suite_example_id: str | None = None,
) -> sqlite3.Row:
    attempt_id = generate_id("attempt")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO model_attempts
            (id, workspace_id, game_id, task, actor, model, provider_alias,
             prompt_version, checkpoint, ply, fen, attempt_number, status,
             raw_response, request_ids_json, json_requested, parse_ok,
             parsed_move, is_legal, applied_move_id, error_detail,
             transport_attempts, json_mode_dropped, reasoning_effort_dropped,
             reply_source, benchmark_run_id, suite_example_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            attempt_id,
            workspace_id,
            game_id,
            task,
            actor,
            model,
            provider_alias,
            prompt_version,
            checkpoint,
            ply,
            fen,
            attempt_number,
            status,
            raw_response,
            json.dumps(list(request_ids)),
            int(json_requested),
            int(parse_ok),
            parsed_move,
            None if is_legal is None else int(is_legal),
            applied_move_id,
            error_detail,
            transport_attempts,
            None if json_mode_dropped is None else int(json_mode_dropped),
            None if reasoning_effort_dropped is None else int(reasoning_effort_dropped),
            reply_source,
            benchmark_run_id,
            suite_example_id,
            created_at,
        ),
    )
    row = get_attempt(conn, attempt_id)
    assert row is not None
    return row


def get_attempt(conn: sqlite3.Connection, attempt_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM model_attempts WHERE id = ?", (attempt_id,)).fetchone()


def list_attempts(
    conn: sqlite3.Connection,
    *,
    workspace_id: str | None = None,
    task: str | None = None,
    actor: str | None = None,
    model: str | None = None,
    game_id: str | None = None,
    checkpoint: str | None = None,
    benchmark_run_id: str | None = None,
) -> list[sqlite3.Row]:
    """Attempts filtered by any combination of scope fields, oldest first."""
    query = "SELECT * FROM model_attempts WHERE 1 = 1"
    params: list[str] = []
    for column, value in [
        ("workspace_id", workspace_id),
        ("task", task),
        ("actor", actor),
        ("model", model),
        ("game_id", game_id),
        ("checkpoint", checkpoint),
        ("benchmark_run_id", benchmark_run_id),
    ]:
        if value is not None:
            query += f" AND {column} = ?"
            params.append(value)
    query += " ORDER BY created_at, attempt_number"
    return conn.execute(query, params).fetchall()


def delete_attempts_for_workspace(conn: sqlite3.Connection, workspace_id: str) -> None:
    conn.execute("DELETE FROM model_attempts WHERE workspace_id = ?", (workspace_id,))
