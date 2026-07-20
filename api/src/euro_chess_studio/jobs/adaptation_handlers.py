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
import os
import sqlite3
import time
from dataclasses import asdict, dataclass

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
from euro_chess_studio.jobs.metric_persistence import record_benchmark_metric

# A benchmark example is one prompt with no game clock behind it; a
# stuck provider should fail the example, not stall the whole run.
BENCHMARK_CALL_TIMEOUT_SECONDS = 15.0
# The whole live run is bounded too (BENCHMARK_RUN_DEADLINE_SECONDS,
# clamped 10-300): per-example timeouts alone would let a slow provider
# hold the presenter's screen for minutes.
BENCHMARK_RUN_DEADLINE_DEFAULT_SECONDS = 60.0
# A provider that fails this many examples in a row is down; stop
# burning the deadline on it.
BENCHMARK_MAX_CONSECUTIVE_FAILURES = 3


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


@dataclass(frozen=True)
class _GatheredReply:
    """One example's outcome from the gather phase: either a raw reply
    or a transport failure, with whatever provenance the source carried.
    Gathering is pure collection -- by the time anything touches the
    database, every network call is already over."""

    example: dict
    reply_source: str
    raw_response: str | None
    request_ids: tuple[str, ...] = ()
    transport_attempts: int | None = None
    json_mode_dropped: bool | None = None
    reasoning_effort_dropped: bool | None = None
    error_detail: str | None = None


def _run_deadline_seconds() -> float:
    """Overall wall-clock budget for one live benchmark run, across all
    examples. Without it, twelve sequential 15-second timeouts could
    hold the presenter's screen for three minutes."""
    raw = os.environ.get("BENCHMARK_RUN_DEADLINE_SECONDS", "")
    try:
        value = float(raw)
    except ValueError:
        value = BENCHMARK_RUN_DEADLINE_DEFAULT_SECONDS
    return min(300.0, max(10.0, value))


def _gather_live_replies(examples: list[dict]) -> tuple[list[_GatheredReply], str, str]:
    """Calls the provider for every example while holding no database
    state at all. Bounded twice over: one overall run deadline, and an
    abort after consecutive transport failures (a dead provider should
    cost seconds, not the full deadline). Examples never attempted are
    recorded as transport failures naming the reason."""
    # Raises LlmNotConfiguredError before any attempt when no key is
    # set; the route maps it to 503.
    model = llm_client.get_llm_model()
    deadline = time.monotonic() + _run_deadline_seconds()
    consecutive_failures = 0
    aborted_reason: str | None = None
    gathered: list[_GatheredReply] = []
    for example in examples:
        if aborted_reason is None and consecutive_failures >= BENCHMARK_MAX_CONSECUTIVE_FAILURES:
            aborted_reason = f"aborted after {consecutive_failures} consecutive transport failures"
        remaining = deadline - time.monotonic()
        if aborted_reason is None and remaining <= 0:
            aborted_reason = "run deadline exceeded"
        if aborted_reason is not None:
            gathered.append(
                _GatheredReply(
                    example=example,
                    reply_source="live",
                    raw_response=None,
                    error_detail=aborted_reason,
                )
            )
            continue
        try:
            outcome = llm_client.chat(
                [{"role": "user", "content": example["prompt"]}],
                json_response=True,
                timeout=min(BENCHMARK_CALL_TIMEOUT_SECONDS, remaining),
            )
        except llm_client.LlmRequestError as exc:
            consecutive_failures += 1
            gathered.append(
                _GatheredReply(
                    example=example,
                    reply_source="live",
                    raw_response=None,
                    request_ids=exc.request_ids,
                    transport_attempts=exc.transport_attempts,
                    json_mode_dropped=exc.json_mode_dropped,
                    reasoning_effort_dropped=exc.reasoning_effort_dropped,
                    error_detail=str(exc),
                )
            )
            continue
        consecutive_failures = 0
        gathered.append(
            _GatheredReply(
                example=example,
                reply_source="live",
                raw_response=outcome.content,
                request_ids=outcome.request_ids,
                transport_attempts=outcome.attempts,
                json_mode_dropped=outcome.json_mode_dropped,
                reasoning_effort_dropped=outcome.reasoning_effort_dropped,
            )
        )
    return gathered, model, "opponent"


def _gather_replayed_replies(
    suite: sqlite3.Row, examples: list[dict], checkpoint: str
) -> tuple[list[_GatheredReply], str, str]:
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
        raise AdaptationError(f"the replay fixture has no replies for checkpoint '{checkpoint}'")
    gathered: list[_GatheredReply] = []
    for example in examples:
        raw_response = checkpoint_data["replies"].get(example["example_id"])
        if raw_response is None:
            raise AdaptationError(
                f"the replay fixture has no reply for example {example['example_id']}"
            )
        gathered.append(
            _GatheredReply(example=example, reply_source="replayed", raw_response=raw_response)
        )
    return gathered, checkpoint_data["model"], checkpoint_data["provider_alias"]


def _persist_gathered_reply(
    conn: sqlite3.Connection,
    record: _GatheredReply,
    *,
    run_id: str,
    checkpoint: str,
    model: str,
    provider_alias: str,
    prompt_version: str,
) -> None:
    example = record.example
    if record.raw_response is None:
        judgment = None
    else:
        judgment = judge_benchmark_reply(record.raw_response, example["legal_moves"])
    insert_attempt(
        conn,
        workspace_id=None,
        task=BENCHMARK_TASK,
        actor="model",
        attempt_number=1,
        status="scored" if judgment is not None else "transport_failed",
        model=model,
        provider_alias=provider_alias,
        prompt_version=prompt_version,
        checkpoint=checkpoint,
        fen=example["fen"],
        raw_response=record.raw_response,
        request_ids=record.request_ids,
        json_requested=True,
        parse_ok=judgment.parse_ok if judgment is not None else False,
        parsed_move=judgment.parsed_move if judgment is not None else None,
        is_legal=judgment.is_legal if judgment is not None else None,
        error_detail=record.error_detail,
        transport_attempts=record.transport_attempts,
        json_mode_dropped=record.json_mode_dropped,
        reasoning_effort_dropped=record.reasoning_effort_dropped,
        reply_source=record.reply_source,
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

    # Gather first, persist after: a live run makes up to a suite's
    # worth of provider calls, and SQLite's write lock must never be
    # held across a network wait. Nothing below touches the database
    # until every reply (or failure) is already in memory.
    if source == "live":
        if checkpoint != BASE_CHECKPOINT:
            raise AdaptationError(
                "the adapted checkpoint has no live serving path in the "
                "workshop build (the adapter would need merging and GGUF "
                "conversion first); run it replayed"
            )
        gathered, model, provider_alias = _gather_live_replies(examples)
        note = "Live benchmark run against the configured opponent endpoint."
    else:
        gathered, model, provider_alias = _gather_replayed_replies(suite, examples, checkpoint)
        note = (
            "Scripted illustration: replies replayed from the authored "
            "fixture (no model produced them); the metrics are computed "
            "live over those scripted replies."
        )

    run_id = generate_id("benchrun")
    for record in gathered:
        _persist_gathered_reply(
            conn,
            record,
            run_id=run_id,
            checkpoint=checkpoint,
            model=model,
            provider_alias=provider_alias,
            prompt_version=prompt_version,
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
    # Benchmark metrics are immutable history: one insert per run, never
    # replacing an earlier run's rows.
    for result in results:
        record_benchmark_metric(conn, result, run_id)

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
        job_config_id=job.job_config_id,
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
