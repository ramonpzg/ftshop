"""SQLite access for the singleton presenter_state row. No business logic here."""

import sqlite3
from datetime import UTC, datetime

SINGLETON_ID = "singleton"


def get_or_create_presenter_state(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM presenter_state WHERE id = ?", (SINGLETON_ID,)).fetchone()
    if row is not None:
        return row
    # A room joining at once means many requests race past the check
    # above on an empty table. OR IGNORE lets exactly one insert win
    # instead of throwing UNIQUE violations at the rest.
    conn.execute(
        """
        INSERT OR IGNORE INTO presenter_state
            (id, mode, locked, active_page_slug, focused_user_id, updated_at)
        VALUES (?, 'idle', 0, NULL, NULL, ?)
        """,
        (SINGLETON_ID, datetime.now(UTC).isoformat()),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM presenter_state WHERE id = ?", (SINGLETON_ID,)).fetchone()
    assert row is not None
    return row


def update_presenter_state(
    conn: sqlite3.Connection,
    *,
    mode: str | None = None,
    locked: bool | None = None,
    active_page_slug: str | None | object = ...,
) -> sqlite3.Row:
    """Updates only the fields explicitly passed.

    active_page_slug uses `...` (not None) as its "leave unchanged" sentinel,
    since None is itself a valid value (no page focused).
    """
    get_or_create_presenter_state(conn)
    fields: list[str] = []
    values: list[object] = []
    if mode is not None:
        fields.append("mode = ?")
        values.append(mode)
    if locked is not None:
        fields.append("locked = ?")
        values.append(int(locked))
    if active_page_slug is not ...:
        fields.append("active_page_slug = ?")
        values.append(active_page_slug)
    fields.append("updated_at = ?")
    values.append(datetime.now(UTC).isoformat())
    values.append(SINGLETON_ID)
    conn.execute(f"UPDATE presenter_state SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM presenter_state WHERE id = ?", (SINGLETON_ID,)).fetchone()
    assert row is not None
    return row
