"""Handlers for the adaptation evidence chain jobs: the cached training
replay and the frozen-suite benchmark. Run by LocalRunner inside
run_job's single transaction; nothing here commits.

Honesty rules enforced here rather than in the UI:
- the cached training replay only ever claims the dataset it was
  actually recorded against (matched by content hash), and refuses to
  pose as training on anything else;
- a snapshot that shares positions with a held-out suite cannot train;
- replayed benchmark replies are marked replayed on every attempt,
  carry no provider request ids, and never pose as live calls;
- the adapted checkpoint has no live serving path and says so.
"""

import json
import sqlite3
from dataclasses import asdict

from euro_chess_studio.calculations.adaptation import (
    BASE_CHECKPOINT,
    BENCHMARK_TASK,
    AdaptationError,
    get_training_config,
    judge_benchmark_reply,
    overlapping_fens,
)
from euro_chess_studio.calculations.evals import (
    compute_explanation_rate,
    compute_model_legal_move_rate,
    compute_position_set_id,
    compute_valid_json_rate,
)
from euro_chess_studio.calculations.ids import generate_id
from euro_chess_studio.data import llm_client
from euro_chess_studio.data.adaptation_fixtures import (
    load_benchmark_replies_fixture,
    load_training_fixture,
)
from euro_chess_studio.data.adapters_repo import (
    find_adapter,
    get_adapter_by_checkpoint,
    insert_adapter,
)
from euro_chess_studio.data.benchmark_runs_repo import insert_run
from euro_chess_studio.data.dataset_snapshots_repo import get_snapshot
from euro_chess_studio.data.eval_suites_repo import get_suite, list_suites
from euro_chess_studio.data.model_attempts_repo import insert_attempt, list_attempts
from euro_chess_studio.jobs.base import JobConfig, JobOutput
from euro_chess_studio.jobs.metric_persistence import persist_metric

# A benchmark example is one prompt with no game clock behind it; a
# stuck provider should fail the example, not stall the whole run.
BENCHMARK_CALL_TIMEOUT_SECONDS = 15.0


def adapter_payload(row) -> dict:
    data = dict(row)
    data["config"] = json.loads(data.pop("config_json"))
    return data


def text_train_adapter(conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
    snapshot_id = job.params.get("dataset_snapshot_id")
    config_id = job.params.get("config_id")
    if not snapshot_id or not config_id:
        raise AdaptationError("text.train_adapter needs dataset_snapshot_id and config_id")
    snapshot = get_snapshot(conn, snapshot_id)
    if snapshot is None:
        raise AdaptationError(f"unknown dataset snapshot: {snapshot_id}")
    config = get_training_config(config_id)

    fixture = load_training_fixture()
    if fixture["config_hash"] != config.config_hash:
        raise AdaptationError(
            "the cached training result was recorded for a different "
            f"configuration (fixture {fixture['config_hash']}, "
            f"selected {config.config_hash}); it cannot replay as this one"
        )
    if fixture["dataset_content_hash"] != snapshot["content_hash"]:
        raise AdaptationError(
            "the cached training result is bound to the reference snapshot "
            f"(content hash {fixture['dataset_content_hash']}); snapshot "
            f"'{snapshot['label']}' has hash {snapshot['content_hash']} and "
            "no cached result exists for it. Live training is not part of "
            "the workshop build."
        )

    # Training-data identity and evaluation-suite identity are separate.
    # A snapshot that contains a held-out position must not train.
    rows = json.loads(snapshot["rows_json"])
    for suite in list_suites(conn, modality="text"):
        overlap = overlapping_fens(rows, json.loads(suite["examples_json"]))
        if overlap:
            raise AdaptationError(
                f"the snapshot shares {len(overlap)} position(s) with the "
                f"held-out suite '{suite['label']}'; training on the "
                "comparison examples would invalidate the benchmark"
            )

    existing = find_adapter(
        conn,
        modality="text",
        checkpoint=config.target_checkpoint,
        config_hash=config.config_hash,
        dataset_content_hash=snapshot["content_hash"],
    )
    already_trained = existing is not None
    if existing is not None:
        adapter = existing
    else:
        adapter = insert_adapter(
            conn,
            label=config.label,
            modality="text",
            checkpoint=config.target_checkpoint,
            base_model=config.base_model,
            method=config.method,
            seed=config.seed,
            output_task=config.output_task,
            config_id=config.config_id,
            config_hash=config.config_hash,
            config=config.as_dict(),
            dataset_snapshot_id=snapshot["id"],
            dataset_content_hash=snapshot["content_hash"],
            runner="replay",
            result_source="cached",
            limitations=config.limitations,
        )

    return JobOutput(
        modality="text",
        kind="adapter_training",
        cached=True,
        payload={
            "result_source": "cached",
            "already_trained": already_trained,
            "adapter": adapter_payload(adapter),
            "training": fixture["training"],
            "note": fixture["note"],
        },
    )


def _judged_attempt_row(
    conn: sqlite3.Connection,
    *,
    example: dict,
    raw_response: str,
    run_id: str,
    checkpoint: str,
    model: str,
    provider_alias: str,
    prompt_version: str,
    reply_source: str,
    request_ids: tuple[str, ...] = (),
    transport_attempts: int | None = None,
    json_mode_dropped: bool | None = None,
    reasoning_effort_dropped: bool | None = None,
) -> None:
    judgment = judge_benchmark_reply(raw_response, example["legal_moves"])
    insert_attempt(
        conn,
        workspace_id=None,
        task=BENCHMARK_TASK,
        actor="model",
        attempt_number=1,
        status="scored",
        model=model,
        provider_alias=provider_alias,
        prompt_version=prompt_version,
        checkpoint=checkpoint,
        fen=example["fen"],
        raw_response=raw_response,
        request_ids=request_ids,
        json_requested=True,
        parse_ok=judgment.parse_ok,
        parsed_move=judgment.parsed_move,
        is_legal=judgment.is_legal,
        transport_attempts=transport_attempts,
        json_mode_dropped=json_mode_dropped,
        reasoning_effort_dropped=reasoning_effort_dropped,
        reply_source=reply_source,
        benchmark_run_id=run_id,
        suite_example_id=example["example_id"],
    )


def text_benchmark_eval(conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
    suite_id = job.params.get("suite_id")
    if not suite_id:
        raise AdaptationError("text.benchmark_eval needs suite_id")
    checkpoint = job.params.get("checkpoint", BASE_CHECKPOINT)
    source = job.params.get("source", "replayed")
    if source not in ("replayed", "live"):
        raise AdaptationError(f"unknown benchmark source: {source}")

    suite = get_suite(conn, suite_id)
    if suite is None:
        raise AdaptationError(f"unknown evaluation suite: {suite_id}")
    examples = json.loads(suite["examples_json"])
    prompt_version = suite["prompt_version"]

    if checkpoint != BASE_CHECKPOINT:
        adapter = get_adapter_by_checkpoint(conn, "text", checkpoint)
        if adapter is None:
            raise AdaptationError(f"no adapter with checkpoint '{checkpoint}'; train it first")

    run_id = generate_id("benchrun")

    if source == "live":
        if checkpoint != BASE_CHECKPOINT:
            raise AdaptationError(
                "the adapted checkpoint has no live serving path in the "
                "workshop build (the adapter would need merging and GGUF "
                "conversion first); run it replayed"
            )
        # Raises LlmNotConfiguredError before any attempt when no key is
        # set; the route maps it to 503.
        settings_model = llm_client.get_llm_model()
        provider_alias = "opponent"
        model = settings_model
        for example in examples:
            try:
                outcome = llm_client.chat(
                    [{"role": "user", "content": example["prompt"]}],
                    json_response=True,
                    timeout=BENCHMARK_CALL_TIMEOUT_SECONDS,
                )
            except llm_client.LlmRequestError as exc:
                insert_attempt(
                    conn,
                    workspace_id=None,
                    task=BENCHMARK_TASK,
                    actor="model",
                    attempt_number=1,
                    status="transport_failed",
                    model=settings_model,
                    provider_alias=provider_alias,
                    prompt_version=prompt_version,
                    checkpoint=checkpoint,
                    fen=example["fen"],
                    request_ids=exc.request_ids,
                    json_requested=True,
                    error_detail=str(exc),
                    transport_attempts=exc.transport_attempts,
                    json_mode_dropped=exc.json_mode_dropped,
                    reasoning_effort_dropped=exc.reasoning_effort_dropped,
                    reply_source="live",
                    benchmark_run_id=run_id,
                    suite_example_id=example["example_id"],
                )
                continue
            model = outcome.model
            _judged_attempt_row(
                conn,
                example=example,
                raw_response=outcome.content,
                run_id=run_id,
                checkpoint=checkpoint,
                model=outcome.model,
                provider_alias=outcome.provider_alias,
                prompt_version=prompt_version,
                reply_source="live",
                request_ids=outcome.request_ids,
                transport_attempts=outcome.attempts,
                json_mode_dropped=outcome.json_mode_dropped,
                reasoning_effort_dropped=outcome.reasoning_effort_dropped,
            )
        note = "Live benchmark run against the configured opponent endpoint."
    else:
        fixture = load_benchmark_replies_fixture()
        if fixture["suite_content_hash"] != suite["content_hash"]:
            raise AdaptationError(
                "the replay fixture was recorded for a different suite "
                f"(fixture {fixture['suite_content_hash']}, suite "
                f"{suite['content_hash']}); a replayed run cannot pose as "
                "answers to these examples"
            )
        checkpoint_data = fixture["checkpoints"].get(checkpoint)
        if checkpoint_data is None:
            raise AdaptationError(
                f"the replay fixture has no replies for checkpoint '{checkpoint}'"
            )
        model = checkpoint_data["model"]
        provider_alias = checkpoint_data["provider_alias"]
        for example in examples:
            raw_response = checkpoint_data["replies"].get(example["example_id"])
            if raw_response is None:
                raise AdaptationError(
                    f"the replay fixture has no reply for example {example['example_id']}"
                )
            _judged_attempt_row(
                conn,
                example=example,
                raw_response=raw_response,
                run_id=run_id,
                checkpoint=checkpoint,
                model=model,
                provider_alias=provider_alias,
                prompt_version=prompt_version,
                reply_source="replayed",
            )
        note = (
            "Replies replayed from the reviewed fixture; the metrics are "
            "computed live over those replies."
        )

    attempts = list_attempts(conn, task=BENCHMARK_TASK, benchmark_run_id=run_id)
    replied = [a for a in attempts if a["raw_response"] is not None]
    results = [
        compute_model_legal_move_rate(
            attempts, task=BENCHMARK_TASK, model=model, checkpoint=checkpoint
        ),
        compute_valid_json_rate(attempts, task=BENCHMARK_TASK, model=model, checkpoint=checkpoint),
        compute_explanation_rate(attempts, task=BENCHMARK_TASK, model=model, checkpoint=checkpoint),
    ]
    for result in results:
        persist_metric(conn, None, result, run_id)

    position_set_id = compute_position_set_id([a["fen"] for a in replied])
    run_row = insert_run(
        conn,
        run_id=run_id,
        suite_id=suite["id"],
        suite_content_hash=suite["content_hash"],
        prompt_version=prompt_version,
        checkpoint=checkpoint,
        model=model,
        provider_alias=provider_alias,
        source=source,
        example_count=len(examples),
        reply_count=len(replied),
        transport_failed_count=len(examples) - len(replied),
        position_set_id=position_set_id,
        note=note,
    )

    return JobOutput(
        modality="text",
        kind="benchmark_eval",
        cached=source == "replayed",
        payload={
            "run_id": run_id,
            "source": source,
            "checkpoint": checkpoint,
            "model": model,
            "suite": {
                "id": suite["id"],
                "label": suite["label"],
                "content_hash": suite["content_hash"],
                "prompt_version": prompt_version,
                "position_set_id": suite["position_set_id"],
            },
            "example_count": len(examples),
            "reply_count": len(replied),
            "transport_failed_count": len(examples) - len(replied),
            "position_set_id": position_set_id,
            "metrics": [asdict(result) for result in results],
            "examples": [
                {
                    "example_id": a["suite_example_id"],
                    "fen": a["fen"],
                    "status": a["status"],
                    "parsed_move": a["parsed_move"],
                    "is_legal": None if a["is_legal"] is None else bool(a["is_legal"]),
                    "reply_source": a["reply_source"],
                }
                for a in attempts
            ],
            "note": note,
            "created_at": run_row["created_at"],
        },
    )
