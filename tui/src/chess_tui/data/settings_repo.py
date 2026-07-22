"""settings table access: small key-value pairs, currently just the
player's name. Reads and writes only; no commits."""

import sqlite3

PLAYER_NAME_KEY = "player_name"


def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    rows = list(conn.execute("SELECT value FROM settings WHERE key = ?", (key,)))
    return rows[0]["value"] if rows else None


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
