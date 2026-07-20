"""Actions for the adaptation evidence chain: freeze a dataset snapshot
from the room's play, seed the reviewed reference fixtures, and
assemble the state the adaptation panel renders."""

import json
import sqlite3
from dataclasses import asdict

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
from euro_chess_studio.calculations.export import build_sft_rows
from euro_chess_studio.data import llm_client
from euro_chess_studio.data.adaptation_fixtures import (
    load_eval_suite_fixture,
    load_reference_snapshot_fixture,
)
from euro_chess_studio.data.adapters_repo import list_adapters
from euro_chess_studio.data.benchmark_runs_repo import (
    latest_run_for_checkpoint,
    list_runs,
)
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
    base_run = latest_run_for_checkpoint(conn, suite["id"], BASE_CHECKPOINT)
    adapted_run = None
    for run in reversed(list_runs(conn, suite_id=suite["id"])):
        if run["checkpoint"] != BASE_CHECKPOINT:
            adapted_run = run
            break
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


def get_adaptation_state(conn: sqlite3.Connection) -> dict:
    """Everything the adaptation panel renders, in one response: the
    frozen datasets, the config catalog, adapters with provenance,
    suites, benchmark runs with their metric rows, and the current
    base-versus-adapted comparison when both runs exist."""
    suites = list_suites(conn, modality="text")
    comparison = None
    for suite in suites:
        comparison = _build_comparison(conn, suite)
        if comparison is not None:
            break
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
        },
    }
