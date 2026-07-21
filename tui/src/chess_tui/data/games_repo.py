"""games table access. Reads and writes only; no commits."""

import sqlite3


def insert_game(
    conn: sqlite3.Connection,
    game_id: str,
    started_at: str,
    model: str,
    prompt_version: str,
) -> None:
    conn.execute(
        "INSERT INTO games (id, started_at, model, prompt_version) VALUES (?, ?, ?, ?)",
        (game_id, started_at, model, prompt_version),
    )


def finish_game(
    conn: sqlite3.Connection,
    game_id: str,
    ended_at: str,
    result: str,
    termination: str,
    duration_seconds: float,
) -> None:
    conn.execute(
        "UPDATE games SET ended_at = ?, result = ?, termination = ?, duration_seconds = ? "
        "WHERE id = ?",
        (ended_at, result, termination, duration_seconds, game_id),
    )


def list_games_newest_first(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT g.*, COUNT(p.id) AS ply_count FROM games g "
            "LEFT JOIN plies p ON p.game_id = g.id "
            "GROUP BY g.id ORDER BY g.started_at DESC, g.rowid DESC"
        )
    )


def get_game(conn: sqlite3.Connection, game_id: str) -> sqlite3.Row | None:
    rows = list(conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)))
    return rows[0] if rows else None


def game_results(conn: sqlite3.Connection) -> list[str | None]:
    return [row["result"] for row in conn.execute("SELECT result FROM games")]
