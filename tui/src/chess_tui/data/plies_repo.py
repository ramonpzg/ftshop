"""plies table access. Reads and writes only; no commits."""

import sqlite3


def insert_ply(
    conn: sqlite3.Connection,
    game_id: str,
    ply: int,
    actor: str,
    uci: str,
    san: str,
    fen_before: str,
    fen_after: str,
    is_capture: bool,
    comment: str | None,
    created_at: str,
) -> None:
    conn.execute(
        "INSERT INTO plies (game_id, ply, actor, uci, san, fen_before, fen_after, "
        "is_capture, comment, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            game_id,
            ply,
            actor,
            uci,
            san,
            fen_before,
            fen_after,
            int(is_capture),
            comment,
            created_at,
        ),
    )


def plies_for_game(conn: sqlite3.Connection, game_id: str) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM plies WHERE game_id = ? ORDER BY ply", (game_id,)))


def participant_captures_by_game(conn: sqlite3.Connection) -> list[tuple[str | None, int]]:
    """Per game: its result and how many captures the participant made
    in it. Mechanical retrieval; the rules live in calculations.stats."""
    return [
        (row["result"], row["captures"])
        for row in conn.execute(
            "SELECT g.result AS result, "
            "COALESCE(SUM(CASE WHEN p.actor = 'participant' THEN p.is_capture END), 0) "
            "AS captures FROM games g LEFT JOIN plies p ON p.game_id = g.id GROUP BY g.id"
        )
    ]
