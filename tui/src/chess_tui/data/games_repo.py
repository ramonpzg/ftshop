"""games table access. Reads and writes only; no commits."""

import sqlite3


def insert_game(
    conn: sqlite3.Connection,
    game_id: str,
    started_at: str,
    model: str,
    prompt_version: str,
    participant_color: str,
    player_name: str,
) -> None:
    conn.execute(
        "INSERT INTO games (id, started_at, model, prompt_version, participant_color, "
        "player_name) VALUES (?, ?, ?, ?, ?, ?)",
        (game_id, started_at, model, prompt_version, participant_color, player_name),
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


def claim_unnamed_games(conn: sqlite3.Connection, player_name: str) -> None:
    """Games recorded before the name feature belong to whoever names
    themselves first on this device. It is a phone, not a tournament."""
    conn.execute("UPDATE games SET player_name = ? WHERE player_name IS NULL", (player_name,))


def list_games_newest_first(
    conn: sqlite3.Connection, player_name: str | None = None
) -> list[sqlite3.Row]:
    where = "WHERE g.player_name = ?" if player_name is not None else ""
    params = (player_name,) if player_name is not None else ()
    return list(
        conn.execute(
            "SELECT g.*, COUNT(p.id) AS ply_count FROM games g "
            f"LEFT JOIN plies p ON p.game_id = g.id {where} "
            "GROUP BY g.id ORDER BY g.started_at DESC, g.rowid DESC",
            params,
        )
    )


def get_game(conn: sqlite3.Connection, game_id: str) -> sqlite3.Row | None:
    rows = list(conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)))
    return rows[0] if rows else None


def game_results(
    conn: sqlite3.Connection, player_name: str | None = None
) -> list[tuple[str | None, str]]:
    """(result, participant_color) per game, optionally for one player."""
    where = "WHERE player_name = ?" if player_name is not None else ""
    params = (player_name,) if player_name is not None else ()
    return [
        (row["result"], row["participant_color"])
        for row in conn.execute(f"SELECT result, participant_color FROM games {where}", params)
    ]
