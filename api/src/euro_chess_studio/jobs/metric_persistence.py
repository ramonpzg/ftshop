"""Shared persistence for computed MetricResults. Used by every job
handler that turns calculations into stored eval_results rows; runs
inside run_job's transaction and never commits."""

import json
import sqlite3

from euro_chess_studio.calculations.evals import MetricResult, compute_position_set_id
from euro_chess_studio.data.eval_results_repo import (
    delete_eval_result,
    insert_eval_result,
    replace_eval_result,
)


def persist_metric(
    conn: sqlite3.Connection, workspace_id: str | None, result: MetricResult, run_id: str
) -> None:
    """An available metric replaces any prior result for its exact scope
    and position set (model, checkpoint, which positions it covered, and
    the rest of the identity together): the same window re-run updates
    in place, a genuinely different window (a different position set)
    coexists instead of overwriting. An unavailable metric removes every
    window's prior result for the scope instead of leaving one on
    display: an empty sample must not keep showing a stale number from
    before the data disappeared (a page reset, for instance), and has no
    position set to target a single window's row with anyway."""
    model = result.scope.get("model")
    checkpoint = result.scope.get("checkpoint")
    if not result.available or result.value is None:
        delete_eval_result(
            conn,
            modality="text",
            metric=result.metric,
            workspace_id=workspace_id,
            source="computed",
            model=model,
            checkpoint=checkpoint,
        )
        return
    position_set_id = compute_position_set_id(result.positions)
    replace_eval_result(
        conn,
        modality="text",
        metric=result.metric,
        value=result.value,
        workspace_id=workspace_id,
        source="computed",
        numerator=result.numerator,
        denominator=result.denominator,
        unit=result.unit,
        direction=result.direction,
        definition=result.definition,
        version=result.version,
        scope_json=json.dumps(result.scope),
        model=model,
        checkpoint=checkpoint,
        run_id=run_id,
        sample_ids_json=json.dumps(list(result.sample_ids)),
        position_set_id=position_set_id,
        position_set_json=json.dumps(list(result.positions)),
    )


def record_benchmark_metric(conn: sqlite3.Connection, result: MetricResult, run_id: str) -> None:
    """Benchmark metrics are immutable history: one insert per run, so a
    re-run of the same suite and checkpoint adds rows next to the old
    run's instead of replacing them, and every benchmark_runs row keeps
    resolving its own metrics forever. An unavailable metric (a live run
    where nothing replied) records no row; the run row itself carries
    the zero reply count."""
    if not result.available or result.value is None:
        return
    model = result.scope.get("model")
    checkpoint = result.scope.get("checkpoint")
    insert_eval_result(
        conn,
        modality="text",
        metric=result.metric,
        value=result.value,
        workspace_id=None,
        source="computed",
        numerator=result.numerator,
        denominator=result.denominator,
        unit=result.unit,
        direction=result.direction,
        definition=result.definition,
        version=result.version,
        scope_json=json.dumps(result.scope),
        model=model,
        checkpoint=checkpoint,
        run_id=run_id,
        sample_ids_json=json.dumps(list(result.sample_ids)),
        position_set_id=compute_position_set_id(result.positions),
        position_set_json=json.dumps(list(result.positions)),
    )
