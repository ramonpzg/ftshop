"""SQLite access for the scenario_assessments table. No business logic
here; the caller owns the transaction. The suggested_* columns are
written once and never updated; participant review only touches status,
the final_* columns, and updated_at."""

import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_scenario(
    conn: sqlite3.Connection,
    *,
    workspace_id: str,
    ply: int,
    fen: str,
    status: str,
    game_id: str | None = None,
    attempt_id: str | None = None,
    suggested_assessment: str | None = None,
    suggested_real_world: str | None = None,
    suggested_video_prompt: str | None = None,
    model: str | None = None,
    provider_alias: str | None = None,
    prompt_version: str | None = None,
    error_detail: str | None = None,
) -> sqlite3.Row:
    scenario_id = generate_id("scenario")
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO scenario_assessments
            (id, workspace_id, game_id, attempt_id, ply, fen, status,
             suggested_assessment, suggested_real_world, suggested_video_prompt,
             model, provider_alias, prompt_version, error_detail,
             created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scenario_id,
            workspace_id,
            game_id,
            attempt_id,
            ply,
            fen,
            status,
            suggested_assessment,
            suggested_real_world,
            suggested_video_prompt,
            model,
            provider_alias,
            prompt_version,
            error_detail,
            now,
            now,
        ),
    )
    row = get_scenario(conn, scenario_id)
    assert row is not None
    return row


def get_scenario(conn: sqlite3.Connection, scenario_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM scenario_assessments WHERE id = ?", (scenario_id,)
    ).fetchone()


def set_review(
    conn: sqlite3.Connection,
    scenario_id: str,
    *,
    status: str,
    final_assessment: str,
    final_real_world: str,
    final_video_prompt: str,
) -> sqlite3.Row:
    """Records the participant's accept or edit. The suggested_* columns
    stay untouched."""
    updated_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        UPDATE scenario_assessments
        SET status = ?, final_assessment = ?, final_real_world = ?,
            final_video_prompt = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, final_assessment, final_real_world, final_video_prompt, updated_at, scenario_id),
    )
    row = get_scenario(conn, scenario_id)
    assert row is not None
    return row


def latest_scenario(conn: sqlite3.Connection, workspace_id: str) -> sqlite3.Row | None:
    """The single latest scenario for a workspace, for reload -- whatever
    its status, including 'failed'. A failure is a fact about the last
    attempt; hiding it would make reload silently forget it happened
    and show the pristine empty state instead of the recoverable error
    state a live failure shows."""
    return conn.execute(
        """
        SELECT * FROM scenario_assessments
        WHERE workspace_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (workspace_id,),
    ).fetchone()


def latest_successful_scenario(conn: sqlite3.Connection, workspace_id: str) -> sqlite3.Row | None:
    """The latest scenario that actually produced a usable mapping,
    skipping over any more recent failure. A live failure leaves the
    previous mapping displayed alongside the new error; reload needs
    this row (together with latest_scenario) to reconstruct that same
    combination instead of only ever surfacing whichever row happens to
    be most recent."""
    return conn.execute(
        """
        SELECT * FROM scenario_assessments
        WHERE workspace_id = ? AND status != 'failed'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (workspace_id,),
    ).fetchone()


def list_scenarios(
    conn: sqlite3.Connection, *, workspace_id: str | None = None
) -> list[sqlite3.Row]:
    if workspace_id is not None:
        return conn.execute(
            "SELECT * FROM scenario_assessments WHERE workspace_id = ? ORDER BY created_at",
            (workspace_id,),
        ).fetchall()
    return conn.execute("SELECT * FROM scenario_assessments ORDER BY created_at").fetchall()


def delete_scenarios_for_workspace(conn: sqlite3.Connection, workspace_id: str) -> None:
    conn.execute("DELETE FROM scenario_assessments WHERE workspace_id = ?", (workspace_id,))
