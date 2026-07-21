"""Actions for the adaptation evidence chain: freeze a dataset snapshot
from the room's play, seed the reviewed reference fixtures, and
assemble the state the adaptation panel renders."""

import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime

from euro_chess_studio.calculations.adaptation import (
    BASE_CHECKPOINT,
    SNAPSHOT_SCHEMA_VERSION,
    TRAINING_CONFIGS,
    AdaptationError,
    build_snapshot,
    compute_snapshot_content_hash,
    overlapping_fens,
    validate_suite_examples,
)
from euro_chess_studio.calculations.comparison import (
    build_example_comparisons,
    check_run_comparability,
    compare_metric_rows,
)
from euro_chess_studio.calculations.export import SFT_PROMPT_VERSION, build_sft_rows
from euro_chess_studio.calculations.generation import LIVE_BENCHMARK_LOCK_KEY
from euro_chess_studio.data import llm_client
from euro_chess_studio.data.adaptation_fixtures import (
    load_eval_suite_fixture,
    load_reference_snapshot_fixture,
)
from euro_chess_studio.data.adapters_repo import list_adapters
from euro_chess_studio.data.benchmark_runs_repo import list_runs
from euro_chess_studio.data.dataset_rows_repo import (
    list_dataset_rows_by_shape_with_move_provenance,
)
from euro_chess_studio.data.dataset_snapshots_repo import (
    get_snapshot_by_content_hash,
    insert_snapshot,
    list_snapshots,
)
from euro_chess_studio.data.eval_results_repo import list_eval_results_by_run
from euro_chess_studio.data.eval_suites_repo import (
    get_suite_by_content_hash,
    insert_suite,
    list_suites,
)
from euro_chess_studio.data.model_attempts_repo import list_attempts
from euro_chess_studio.data.run_locks_repo import get_lock
from euro_chess_studio.data.scenario_repo import list_scenarios


def freeze_dataset_snapshot(conn: sqlite3.Connection, *, label: str | None = None) -> sqlite3.Row:
    """Freezes the room's current training-eligible rows into a durable,
    hashed snapshot. Owns its transaction (single-write path).

    The eligibility rule is phase 33's: fallback and unknown actors stay
    in the audit archive but never enter the SFT snapshot. Scenario
    mappings ride along as raw versus participant-approved counts so the
    two are never conflated."""
    dataset_rows = list_dataset_rows_by_shape_with_move_provenance(conn, "fen_legal_moves_to_move")
    sft_rows_by_id: dict[str, dict] = {}
    for row in dataset_rows:
        payload = json.loads(row["payload_json"])
        payload["actor"] = row["move_actor"]
        built = build_sft_rows([payload])
        if built:
            sft_rows_by_id[row["id"]] = built[0]
    build = build_snapshot(dataset_rows, sft_rows_by_id)
    if build.row_count == 0:
        raise AdaptationError("no training-eligible rows to freeze; play some legal moves first")

    scenarios = list_scenarios(conn)
    raw_count = sum(1 for s in scenarios if s["status"] != "failed")
    approved_count = sum(1 for s in scenarios if s["status"] in ("accepted", "edited"))

    existing = list_snapshots(conn, modality="text")
    resolved_label = label or f"room-{sum(1 for s in existing if s['origin'] == 'frozen') + 1:02d}"
    try:
        snapshot = insert_snapshot(
            conn,
            label=resolved_label,
            modality="text",
            origin="frozen",
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            row_count=build.row_count,
            excluded_ineligible_count=build.excluded_ineligible_count,
            source_game_count=build.source_game_count,
            source_workspace_count=build.source_workspace_count,
            scenario_raw_count=raw_count,
            scenario_approved_count=approved_count,
            content_hash=build.content_hash,
            rows=build.rows,
            source_row_ids=build.source_row_ids,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return snapshot


def seed_adaptation_fixtures(conn: sqlite3.Connection) -> int:
    """Seeds the reviewed reference snapshot and held-out suite,
    idempotent by content hash. Fails loudly if the fixtures drift into
    overlapping each other: a suite the training set contains is not
    held out, and that is an authoring error to fix, not to store."""
    seeded = 0
    snapshot_fixture = load_reference_snapshot_fixture()
    rows = snapshot_fixture["rows"]
    content_hash = compute_snapshot_content_hash(rows)

    suite_fixture = load_eval_suite_fixture()
    validation = validate_suite_examples(
        suite_fixture["examples"],
        prompt_version=suite_fixture["prompt_version"],
        schema_version=suite_fixture["schema_version"],
    )
    overlap = overlapping_fens(rows, validation.examples)
    if overlap:
        raise AdaptationError(
            f"fixture drift: the reference snapshot shares {len(overlap)} "
            "position(s) with the held-out suite"
        )

    if get_snapshot_by_content_hash(conn, "text", content_hash) is None:
        insert_snapshot(
            conn,
            label=snapshot_fixture["label"],
            modality="text",
            origin="seeded",
            schema_version=snapshot_fixture["schema_version"],
            row_count=len(rows),
            excluded_ineligible_count=0,
            source_game_count=snapshot_fixture["source_game_count"],
            source_workspace_count=0,
            scenario_raw_count=0,
            scenario_approved_count=0,
            content_hash=content_hash,
            rows=rows,
            source_row_ids=[],
            note=snapshot_fixture.get("note"),
        )
        seeded += 1

    if get_suite_by_content_hash(conn, "text", validation.content_hash) is None:
        insert_suite(
            conn,
            label=suite_fixture["label"],
            modality="text",
            origin="seeded",
            prompt_version=suite_fixture["prompt_version"],
            schema_version=suite_fixture["schema_version"],
            example_count=len(validation.examples),
            content_hash=validation.content_hash,
            position_set_id=validation.position_set_id,
            examples=validation.examples,
            note=suite_fixture.get("note"),
        )
        seeded += 1
    conn.commit()
    return seeded


def _snapshot_view(row: sqlite3.Row) -> dict:
    data = dict(row)
    rows = json.loads(data.pop("rows_json"))
    data.pop("source_row_ids_json")
    data["row_preview"] = rows[:3]
    return data


def _suite_view(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["examples"] = json.loads(data.pop("examples_json"))
    # A suite frozen under an older prompt contract stays stored (its
    # runs reference it) but must not present as the current benchmark:
    # an upgraded database keeps its sft-v1 suite forever, and the panel
    # needs to know which one this build actually renders and verifies.
    data["current_contract"] = data["prompt_version"] == SFT_PROMPT_VERSION
    return data


def _adapter_view(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["config"] = json.loads(data.pop("config_json"))
    return data


def _metric_view(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["sample_ids"] = json.loads(data.pop("sample_ids_json") or "[]")
    data.pop("position_set_json", None)
    data.pop("scope_json", None)
    return data


def _run_view(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    data = dict(row)
    data["metrics"] = [_metric_view(m) for m in list_eval_results_by_run(conn, row["id"])]
    return data


def _build_comparison(conn: sqlite3.Connection, suite: sqlite3.Row) -> dict | None:
    runs = list_runs(conn, suite_id=suite["id"])
    adapted_run = next(
        (run for run in reversed(runs) if run["checkpoint"] != BASE_CHECKPOINT), None
    )
    base_candidates = [run for run in runs if run["checkpoint"] == BASE_CHECKPOINT]
    # Prefer the latest base run of the adapter's own model lineage: a
    # live run of some other configured model (Luna standing in for
    # Gemma) must not displace an honest before/after pair. When no
    # lineage-matching base exists, keep the latest base anyway so the
    # comparison renders the model-mismatch refusal instead of
    # vanishing.
    base_run = None
    if adapted_run is not None:
        base_run = next(
            (run for run in reversed(base_candidates) if run["model"] == adapted_run["model"]),
            None,
        )
    if base_run is None:
        base_run = base_candidates[-1] if base_candidates else None
    if base_run is None or adapted_run is None:
        return None
    comparability = check_run_comparability(base_run, adapted_run)
    run_level_reason = None if comparability.comparable else "; ".join(comparability.reasons)
    metrics = compare_metric_rows(
        list_eval_results_by_run(conn, base_run["id"]),
        list_eval_results_by_run(conn, adapted_run["id"]),
        run_level_reason=run_level_reason,
    )
    examples = build_example_comparisons(
        json.loads(suite["examples_json"]),
        list_attempts(conn, benchmark_run_id=base_run["id"]),
        list_attempts(conn, benchmark_run_id=adapted_run["id"]),
    )
    return {
        "suite_id": suite["id"],
        "suite_label": suite["label"],
        "base_run": dict(base_run),
        "adapted_run": dict(adapted_run),
        "comparable": comparability.comparable,
        "reasons": list(comparability.reasons),
        "metrics": [asdict(m) for m in metrics],
        "examples": examples,
    }


def _live_benchmark_in_progress(conn: sqlite3.Connection) -> bool:
    """Whether a live benchmark run is in flight right now, read from
    the durable single-flight record run_job commits before the first
    provider call. This is what lets a reloaded panel or a second tab
    render the truth instead of whatever its own React state remembers.
    A row past its expiry is a crashed run and reads as not in
    progress, so controls never stay dead for a run nobody is
    waiting on."""
    row = get_lock(conn, LIVE_BENCHMARK_LOCK_KEY)
    return row is not None and datetime.fromisoformat(row["expires_at"]) > datetime.now(UTC)


def get_adaptation_state(conn: sqlite3.Connection) -> dict:
    """Everything the adaptation panel renders, in one response: the
    frozen datasets, the config catalog, adapters with provenance,
    suites, benchmark runs with their metric rows, and the current
    base-versus-adapted comparison when both runs exist."""
    # Current-contract suites first (newest first within each group): an
    # upgraded database keeps every suite it ever seeded, and "the first
    # suite" is what the panel treats as the benchmark. Choosing "the
    # first suite with a comparison" here used to resurface an obsolete
    # sft-v1 suite just because its old runs still existed; the
    # comparison now belongs to the primary suite or nobody.
    suites = sorted(
        sorted(list_suites(conn, modality="text"), key=lambda s: s["created_at"], reverse=True),
        key=lambda s: s["prompt_version"] != SFT_PROMPT_VERSION,
    )
    comparison = _build_comparison(conn, suites[0]) if suites else None
    return {
        "snapshots": [_snapshot_view(s) for s in list_snapshots(conn, modality="text")],
        "configs": [
            {
                **config.as_dict(),
                "config_hash": config.config_hash,
                "limitations": config.limitations,
            }
            for config in TRAINING_CONFIGS
        ],
        "adapters": [_adapter_view(a) for a in list_adapters(conn, modality="text")],
        "suites": [_suite_view(s) for s in suites],
        "runs": [
            _run_view(conn, run)
            for suite in suites
            for run in list_runs(conn, suite_id=suite["id"])
        ],
        "comparison": comparison,
        "live_benchmark": {
            "available": llm_client.is_llm_configured(),
            "model": llm_client.get_llm_model() if llm_client.is_llm_configured() else None,
            "in_progress": _live_benchmark_in_progress(conn),
        },
    }
