"""SQLite access for the users table. No business logic here."""

import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_user(conn: sqlite3.Connection, name: str) -> sqlite3.Row:
    user_id = generate_id("user")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT INTO users (id, name, created_at) VALUES (?, ?, ?)",
        (user_id, name, created_at),
    )
    conn.commit()
    row = get_user(conn, user_id)
    assert row is not None
    return row


def get_user(conn: sqlite3.Connection, user_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_users(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM users ORDER BY created_at").fetchall()
