"""SQLite access for the run_locks table. No business logic here: the
caller decides what a lock means, when a row counts as expired, and
when to commit. Insert is a plain INSERT so the primary key stays the
arbiter when two requests race for the same key."""

import sqlite3


def get_lock(conn: sqlite3.Connection, lock_key: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM run_locks WHERE lock_key = ?", (lock_key,)).fetchone()


def insert_lock(
    conn: sqlite3.Connection, lock_key: str, *, acquired_at: str, expires_at: str
) -> None:
    conn.execute(
        "INSERT INTO run_locks (lock_key, acquired_at, expires_at) VALUES (?, ?, ?)",
        (lock_key, acquired_at, expires_at),
    )


def delete_lock(conn: sqlite3.Connection, lock_key: str) -> None:
    conn.execute("DELETE FROM run_locks WHERE lock_key = ?", (lock_key,))


def clear_all_locks(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM run_locks")
