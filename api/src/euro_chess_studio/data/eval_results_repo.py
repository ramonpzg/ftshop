"""SQLite access for the eval_results table. No business logic here;
the caller owns the transaction."""

import sqlite3
from datetime import UTC, datetime

from euro_chess_studio.calculations.ids import generate_id


def insert_eval_result(
    conn: sqlite3.Connection,
    *,
    modality: str,
    metric: str,
    value: float,
    workspace_id: str | None,
    source: str,
    numerator: int | None = None,
    denominator: int | None = None,
    unit: str | None = None,
    direction: str | None = None,
    definition: str | None = None,
    version: str | None = None,
    scope_json: str | None = None,
    note: str | None = None,
    model: str | None = None,
    checkpoint: str | None = None,
    run_id: str | None = None,
    sample_ids_json: str | None = None,
    position_set_id: str | None = None,
    position_set_json: str | None = None,
) -> sqlite3.Row:
    result_id = generate_id("eval")
    created_at = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO eval_results
            (id, modality, metric, value, workspace_id, source, numerator,
             denominator, unit, direction, definition, version, scope_json,
             note, model, checkpoint, run_id, sample_ids_json,
             position_set_id, position_set_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result_id,
            modality,
            metric,
            value,
            workspace_id,
            source,
            numerator,
            denominator,
            unit,
            direction,
            definition,
            version,
            scope_json,
            note,
            model,
            checkpoint,
            run_id,
            sample_ids_json,
            position_set_id,
            position_set_json,
            created_at,
        ),
    )
    row = conn.execute("SELECT * FROM eval_results WHERE id = ?", (result_id,)).fetchone()
    assert row is not None
    return row


def _scope_clause() -> str:
    # Everything that identifies "this metric, for this model/checkpoint,
    # in this workspace" without regard to which positions it covered.
    # Used to clear every window under a scope when the underlying data
    # disappears entirely (delete_eval_result): if there is now zero
    # data for the scope, no previously recorded window for it is still
    # trustworthy either.
    return (
        "modality = ? AND metric = ? AND source = ? AND workspace_id IS ? "
        "AND model IS ? AND checkpoint IS ?"
    )


def _scoped_identity_clause() -> str:
    # A row's full identity: the scope above, plus which position set
    # (evaluation window) produced it. Same scope, same position set ->
    # the same measurement re-run, and replaces in place. Same scope, a
    # different position set -> a different window, and coexists rather
    # than overwriting -- the fix for two evaluation windows on the same
    # model/checkpoint silently clobbering each other.
    return f"{_scope_clause()} AND position_set_id IS ?"


def delete_eval_result(
    conn: sqlite3.Connection,
    *,
    modality: str,
    metric: str,
    workspace_id: str | None,
    source: str,
    model: str | None = None,
    checkpoint: str | None = None,
) -> None:
    """Removes every window's row for this scope without inserting a
    replacement. Used when a metric becomes unavailable (an empty
    sample): the prior number must not keep showing as if it were
    still current, and an empty sample carries no position set to
    target a single window with."""
    conn.execute(
        f"DELETE FROM eval_results WHERE {_scope_clause()}",
        (modality, metric, source, workspace_id, model, checkpoint),
    )


def replace_eval_result(
    conn: sqlite3.Connection,
    *,
    modality: str,
    metric: str,
    value: float,
    workspace_id: str | None,
    source: str,
    numerator: int | None = None,
    denominator: int | None = None,
    unit: str | None = None,
    direction: str | None = None,
    definition: str | None = None,
    version: str | None = None,
    scope_json: str | None = None,
    note: str | None = None,
    model: str | None = None,
    checkpoint: str | None = None,
    run_id: str | None = None,
    sample_ids_json: str | None = None,
    position_set_id: str | None = None,
    position_set_json: str | None = None,
) -> sqlite3.Row:
    """Insert an eval result, replacing any previous row for the same
    (modality, metric, workspace, source, model, checkpoint,
    position_set_id). Re-running the same scoped eval over the same
    position set updates its number instead of stacking duplicates; a
    differently-scoped result, or the same scope over a different
    position set (a different evaluation window), is a different row
    and coexists."""
    conn.execute(
        f"DELETE FROM eval_results WHERE {_scoped_identity_clause()}",
        (modality, metric, source, workspace_id, model, checkpoint, position_set_id),
    )
    return insert_eval_result(
        conn,
        modality=modality,
        metric=metric,
        value=value,
        workspace_id=workspace_id,
        source=source,
        numerator=numerator,
        denominator=denominator,
        unit=unit,
        direction=direction,
        definition=definition,
        version=version,
        scope_json=scope_json,
        note=note,
        model=model,
        checkpoint=checkpoint,
        run_id=run_id,
        sample_ids_json=sample_ids_json,
        position_set_id=position_set_id,
        position_set_json=position_set_json,
    )


def list_eval_results(
    conn: sqlite3.Connection,
    *,
    modality: str | None = None,
    workspace_id: str | None = None,
) -> list[sqlite3.Row]:
    query = "SELECT * FROM eval_results WHERE 1 = 1"
    params: list[str] = []
    if modality is not None:
        query += " AND modality = ?"
        params.append(modality)
    if workspace_id is not None:
        query += " AND workspace_id = ?"
        params.append(workspace_id)
    query += " ORDER BY created_at"
    return conn.execute(query, params).fetchall()


def list_eval_results_by_run(conn: sqlite3.Connection, run_id: str) -> list[sqlite3.Row]:
    """Every metric row one job execution produced, oldest first. The
    benchmark comparison reads both runs' rows through this rather than
    re-deriving values from whatever the tables contain later."""
    return conn.execute(
        "SELECT * FROM eval_results WHERE run_id = ? ORDER BY created_at", (run_id,)
    ).fetchall()


def delete_cached_eval_results(conn: sqlite3.Connection) -> None:
    """Clears seeded cached eval rows so re-seeding doesn't duplicate them.
    Computed rows (source='computed') are untouched.
    """
    conn.execute("DELETE FROM eval_results WHERE source = 'cached'")


def delete_eval_results_for_workspace(conn: sqlite3.Connection, workspace_id: str) -> None:
    """Clears computed eval results for one workspace. Called when its
    games/moves/attempts are wiped (page reset): a metric computed from
    data that no longer exists must not keep showing on the panel."""
    conn.execute(
        "DELETE FROM eval_results WHERE workspace_id = ? AND source = 'computed'", (workspace_id,)
    )
