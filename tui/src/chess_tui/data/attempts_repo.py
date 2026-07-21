"""model_attempts table access. One immutable row per raw reply or
transport failure. Reads and writes only; no commits. Authorization
headers are never stored, and the schema has no column for them."""

import sqlite3


def next_attempt_number(conn: sqlite3.Connection, game_id: str, ply: int) -> int:
    row = list(
        conn.execute(
            "SELECT COALESCE(MAX(attempt), 0) AS n FROM model_attempts "
            "WHERE game_id = ? AND ply = ?",
            (game_id, ply),
        )
    )[0]
    return int(row["n"]) + 1


def insert_attempt(
    conn: sqlite3.Connection,
    game_id: str,
    ply: int,
    attempt: int,
    corrective: bool,
    status: str,
    raw_reply: str | None,
    parsed_move: str | None,
    comment: str | None,
    request_id: str | None,
    latency_ms: int | None,
    error_detail: str | None,
    created_at: str,
) -> None:
    conn.execute(
        "INSERT INTO model_attempts (game_id, ply, attempt, corrective, status, raw_reply, "
        "parsed_move, comment, request_id, latency_ms, error_detail, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            game_id,
            ply,
            attempt,
            int(corrective),
            status,
            raw_reply,
            parsed_move,
            comment,
            request_id,
            latency_ms,
            error_detail,
            created_at,
        ),
    )


def attempts_for_game(conn: sqlite3.Connection, game_id: str) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT * FROM model_attempts WHERE game_id = ? ORDER BY ply, attempt",
            (game_id,),
        )
    )
