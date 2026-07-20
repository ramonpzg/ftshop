"""SQLite access for the dataset_rows table. No business logic here."""

import json
import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_dataset_row(
    conn: sqlite3.Connection,
    *,
    workspace_id: str,
    move_id: str | None,
    shape: str,
    payload: dict,
) -> sqlite3.Row:
    row_id = generate_id("dsrow")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO dataset_rows (id, workspace_id, move_id, shape, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (row_id, workspace_id, move_id, shape, json.dumps(payload), created_at),
    )
    row = conn.execute("SELECT * FROM dataset_rows WHERE id = ?", (row_id,)).fetchone()
    assert row is not None
    return row


def list_dataset_rows(conn: sqlite3.Connection, workspace_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM dataset_rows WHERE workspace_id = ? ORDER BY created_at",
        (workspace_id,),
    ).fetchall()


# A LEFT JOIN, not INNER: dataset_rows.move_id is nullable in the schema,
# so a row without a resolvable move must still come back (with NULL
# provenance) rather than silently vanish from an export.
_WITH_MOVE_PROVENANCE = """
    SELECT dataset_rows.*,
           moves.game_id AS move_game_id,
           moves.actor AS move_actor,
           moves.model AS move_model
    FROM dataset_rows
    LEFT JOIN moves ON moves.id = dataset_rows.move_id
"""


def list_dataset_rows_by_shape_with_move_provenance(
    conn: sqlite3.Connection, shape: str
) -> list[sqlite3.Row]:
    """Rows of one shape joined with the actor and model of the move
    that produced them, so callers can decide training eligibility
    instead of treating every stored row as an equally valid target."""
    return conn.execute(
        f"{_WITH_MOVE_PROVENANCE} WHERE dataset_rows.shape = ? ORDER BY dataset_rows.created_at",
        (shape,),
    ).fetchall()


def list_all_dataset_rows_with_move_provenance(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every dataset row, every shape, joined with its move's game,
    actor, and model. Used for the instructor's full-archive export so
    each row is traceable back to who produced it."""
    return conn.execute(f"{_WITH_MOVE_PROVENANCE} ORDER BY dataset_rows.created_at").fetchall()


def count_dataset_rows(conn: sqlite3.Connection) -> int:
    (count,) = conn.execute("SELECT COUNT(*) FROM dataset_rows").fetchone()
    return count


def delete_dataset_rows_for_workspace(conn: sqlite3.Connection, workspace_id: str) -> None:
    conn.execute("DELETE FROM dataset_rows WHERE workspace_id = ?", (workspace_id,))
