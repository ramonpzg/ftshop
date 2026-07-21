"""Tests for the training replay and benchmark handlers through the
real run_job action: registry routing, honest cached provenance, the
refusal to pose as training on other data, replayed-versus-live reply
marking, checkpoint-tagged attempts, and position-set integrity."""

import json
from pathlib import Path

import pytest

from euro_chess_studio.actions.adaptation import seed_adaptation_fixtures
from euro_chess_studio.actions.jobs import run_job
from euro_chess_studio.calculations.adaptation import BASE_CHECKPOINT, AdaptationError
from euro_chess_studio.calculations.export import PROMPT_TEMPLATE
from euro_chess_studio.data.dataset_snapshots_repo import insert_snapshot, list_snapshots
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.eval_suites_repo import list_suites
from euro_chess_studio.data.model_attempts_repo import list_attempts
from euro_chess_studio.jobs import adaptation_handlers
from euro_chess_studio.jobs.registry import RUNNER_NAME_BY_JOB_TYPE


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    seed_adaptation_fixtures(conn)
    return conn


def reference_snapshot(conn):
    (snapshot,) = [s for s in list_snapshots(conn, modality="text") if s["origin"] == "seeded"]
    return snapshot


def seeded_suite(conn):
    (suite,) = list_suites(conn, modality="text")
    return suite


def train(conn):
    return run_job(
        conn,
        "text.train_adapter",
        {
            "dataset_snapshot_id": reference_snapshot(conn)["id"],
            "config_id": "text-gemma-lora-v1",
        },
        None,
    )


def test_adaptation_jobs_route_through_the_registry():
    assert RUNNER_NAME_BY_JOB_TYPE["text.train_adapter"] == "local"
    assert RUNNER_NAME_BY_JOB_TYPE["text.benchmark_eval"] == "local"
    assert RUNNER_NAME_BY_JOB_TYPE["image.adaptation_evidence"] == "replay"
    assert RUNNER_NAME_BY_JOB_TYPE["audio.adaptation_evidence"] == "replay"
    assert RUNNER_NAME_BY_JOB_TYPE["video.adaptation_evidence"] == "replay"


def test_train_adapter_records_full_provenance(tmp_path: Path):
    conn = make_conn(tmp_path)
    result = train(conn)
    payload = json.loads(result.artifact["payload_json"])
    assert result.artifact["cached"] == 1
    assert payload["result_source"] == "cached"
    adapter = payload["adapter"]
    snapshot = reference_snapshot(conn)
    assert adapter["dataset_snapshot_id"] == snapshot["id"]
    assert adapter["dataset_content_hash"] == snapshot["content_hash"]
    assert adapter["base_model"] == "google/gemma-4-E2B-it-qat-q4_0-unquantized"
    assert adapter["checkpoint"] == "gemma-chess-sft-v1"
    assert adapter["runner"] == "replay"
    assert adapter["result_source"] == "cached"
    assert adapter["config_hash"]
    assert adapter["limitations"]
    assert adapter["created_at"]


def test_retraining_returns_the_existing_adapter(tmp_path: Path):
    conn = make_conn(tmp_path)
    first = json.loads(train(conn).artifact["payload_json"])
    second = json.loads(train(conn).artifact["payload_json"])
    assert first["already_trained"] is False
    assert second["already_trained"] is True
    assert second["adapter"]["id"] == first["adapter"]["id"]


def test_cached_training_refuses_to_pose_as_other_data(tmp_path: Path):
    conn = make_conn(tmp_path)
    other = insert_snapshot(
        conn,
        label="room-01",
        modality="text",
        origin="frozen",
        schema_version="sft-prompt-completion-v1",
        row_count=1,
        excluded_ineligible_count=0,
        source_game_count=1,
        source_workspace_count=1,
        scenario_raw_count=0,
        scenario_approved_count=0,
        content_hash="deadbeefdeadbeef",
        rows=[{"prompt": "p", "completion": "c"}],
        source_row_ids=["r1"],
    )
    conn.commit()
    with pytest.raises(AdaptationError, match="bound to the reference snapshot"):
        run_job(
            conn,
            "text.train_adapter",
            {"dataset_snapshot_id": other["id"], "config_id": "text-gemma-lora-v1"},
            None,
        )
    # The refusal rolled the whole job back: no config, no artifact.
    assert conn.execute("SELECT COUNT(*) FROM job_configs").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM adapters").fetchone()[0] == 0


def test_training_refuses_a_snapshot_overlapping_the_held_out_suite(tmp_path: Path, monkeypatch):
    conn = make_conn(tmp_path)
    suite = seeded_suite(conn)
    example = json.loads(suite["examples_json"])[0]
    overlapping_row = {
        "prompt": PROMPT_TEMPLATE.format(
            fen=example["fen"], legal_moves=", ".join(example["legal_moves"])
        ),
        "completion": json.dumps({"move": example["legal_moves"][0]}),
    }
    from euro_chess_studio.calculations.adaptation import compute_snapshot_content_hash

    content_hash = compute_snapshot_content_hash([overlapping_row])
    snapshot = insert_snapshot(
        conn,
        label="overlap",
        modality="text",
        origin="frozen",
        schema_version="sft-prompt-completion-v1",
        row_count=1,
        excluded_ineligible_count=0,
        source_game_count=1,
        source_workspace_count=1,
        scenario_raw_count=0,
        scenario_approved_count=0,
        content_hash=content_hash,
        rows=[overlapping_row],
        source_row_ids=["r1"],
    )
    conn.commit()

    # Bind the training fixture to this snapshot's hash so the hash
    # check passes and only the overlap rule can refuse it.
    real_loader = adaptation_handlers.load_training_fixture

    def bound_fixture():
        return {**real_loader(), "dataset_content_hash": content_hash}

    monkeypatch.setattr(adaptation_handlers, "load_training_fixture", bound_fixture)
    with pytest.raises(AdaptationError, match="held-out suite"):
        run_job(
            conn,
            "text.train_adapter",
            {"dataset_snapshot_id": snapshot["id"], "config_id": "text-gemma-lora-v1"},
            None,
        )


def test_replayed_benchmark_marks_replies_and_invents_no_request_ids(tmp_path: Path):
    conn = make_conn(tmp_path)
    train(conn)
    suite = seeded_suite(conn)
    result = run_job(
        conn,
        "text.benchmark_eval",
        {"suite_id": suite["id"], "checkpoint": BASE_CHECKPOINT, "source": "replayed"},
        None,
    )
    payload = json.loads(result.artifact["payload_json"])
    attempts = list_attempts(conn, task="benchmark_move", benchmark_run_id=payload["run_id"])
    assert len(attempts) == suite["example_count"]
    for attempt in attempts:
        assert attempt["reply_source"] == "replayed"
        assert json.loads(attempt["request_ids_json"]) == []
        assert attempt["checkpoint"] == BASE_CHECKPOINT
        assert attempt["model"] == "gemma-4-2b-local"
        assert attempt["workspace_id"] is None
        assert attempt["suite_example_id"]
    assert result.artifact["cached"] == 1


def test_benchmark_metrics_are_scoped_and_position_matched(tmp_path: Path):
    conn = make_conn(tmp_path)
    train(conn)
    suite = seeded_suite(conn)
    base = json.loads(
        run_job(
            conn,
            "text.benchmark_eval",
            {"suite_id": suite["id"], "checkpoint": BASE_CHECKPOINT},
            None,
        ).artifact["payload_json"]
    )
    adapted = json.loads(
        run_job(
            conn,
            "text.benchmark_eval",
            {"suite_id": suite["id"], "checkpoint": "gemma-chess-sft-v1"},
            None,
        ).artifact["payload_json"]
    )
    # Every metric of both runs carries the suite's exact position set.
    for run in (base, adapted):
        assert run["position_set_id"] == suite["position_set_id"]
        for metric in run["metrics"]:
            assert metric["scope"]["task"] == "benchmark_move"
            assert metric["scope"]["checkpoint"] == run["checkpoint"]
    base_metrics = {m["metric"]: m for m in base["metrics"]}
    adapted_metrics = {m["metric"]: m for m in adapted["metrics"]}
    # The authored fixture's known counts: adaptation improves legality
    # and format but regresses explanations. The trade-off is data, not
    # styling.
    assert base_metrics["model_legal_move_rate"]["numerator"] == 7
    assert base_metrics["model_legal_move_rate"]["denominator"] == 12
    assert adapted_metrics["model_legal_move_rate"]["numerator"] == 12
    assert base_metrics["explanation_rate"]["numerator"] == 8
    assert adapted_metrics["explanation_rate"]["numerator"] == 0


def test_benchmark_requires_a_trained_adapter_for_adapted_checkpoints(tmp_path: Path):
    conn = make_conn(tmp_path)
    suite = seeded_suite(conn)
    with pytest.raises(AdaptationError, match="train it first"):
        run_job(
            conn,
            "text.benchmark_eval",
            {"suite_id": suite["id"], "checkpoint": "gemma-chess-sft-v1"},
            None,
        )


def test_live_benchmark_refuses_the_adapted_checkpoint(tmp_path: Path):
    conn = make_conn(tmp_path)
    train(conn)
    suite = seeded_suite(conn)
    with pytest.raises(AdaptationError, match="no live serving path"):
        run_job(
            conn,
            "text.benchmark_eval",
            {"suite_id": suite["id"], "checkpoint": "gemma-chess-sft-v1", "source": "live"},
            None,
        )


def test_live_benchmark_records_live_provenance(tmp_path: Path, monkeypatch):
    from euro_chess_studio.data.llm_client import ChatOutcome

    conn = make_conn(tmp_path)
    suite = seeded_suite(conn)
    calls = []

    def fake_chat(messages, *, json_response=False, timeout=None, model=None):
        calls.append(messages)
        return ChatOutcome(
            content='{"move": "a2a3"}',
            model="gpt-5.6-luna",
            provider_alias="opponent",
            attempts=1,
            request_ids=(f"req-{len(calls)}",),
            json_mode_requested=True,
            json_mode_sent=True,
            json_mode_dropped=False,
            reasoning_effort_dropped=False,
        )

    monkeypatch.setattr(adaptation_handlers.llm_client, "chat", fake_chat)
    monkeypatch.setattr(adaptation_handlers.llm_client, "get_llm_model", lambda: "gpt-5.6-luna")
    result = run_job(
        conn,
        "text.benchmark_eval",
        {"suite_id": suite["id"], "checkpoint": BASE_CHECKPOINT, "source": "live"},
        None,
    )
    payload = json.loads(result.artifact["payload_json"])
    assert payload["source"] == "live"
    assert result.artifact["cached"] == 0
    attempts = list_attempts(conn, task="benchmark_move", benchmark_run_id=payload["run_id"])
    assert len(calls) == suite["example_count"]
    for attempt in attempts:
        assert attempt["reply_source"] == "live"
        assert json.loads(attempt["request_ids_json"])
        assert attempt["model"] == "gpt-5.6-luna"
    # Each call sent the frozen rendered prompt, not a rebuilt one.
    examples = json.loads(suite["examples_json"])
    assert calls[0][0]["content"] == examples[0]["prompt"]


def test_live_transport_failure_shrinks_the_position_set(tmp_path: Path, monkeypatch):
    from euro_chess_studio.data.llm_client import ChatOutcome, LlmRequestError

    conn = make_conn(tmp_path)
    suite = seeded_suite(conn)
    state = {"count": 0}

    def flaky_chat(messages, *, json_response=False, timeout=None, model=None):
        state["count"] += 1
        if state["count"] == 1:
            raise LlmRequestError(
                "provider unreachable",
                status_code=None,
                request_ids=(),
                transport_attempts=3,
            )
        return ChatOutcome(
            content='{"move": "a2a3"}',
            model="gpt-5.6-luna",
            provider_alias="opponent",
            attempts=1,
            request_ids=("req-x",),
            json_mode_requested=True,
            json_mode_sent=True,
            json_mode_dropped=False,
            reasoning_effort_dropped=False,
        )

    monkeypatch.setattr(adaptation_handlers.llm_client, "chat", flaky_chat)
    monkeypatch.setattr(adaptation_handlers.llm_client, "get_llm_model", lambda: "gpt-5.6-luna")
    payload = json.loads(
        run_job(
            conn,
            "text.benchmark_eval",
            {"suite_id": suite["id"], "checkpoint": BASE_CHECKPOINT, "source": "live"},
            None,
        ).artifact["payload_json"]
    )
    assert payload["transport_failed_count"] == 1
    assert payload["reply_count"] == suite["example_count"] - 1
    # A failed example never entered the denominator, so this run's
    # position set is honestly different from the full suite's.
    assert payload["position_set_id"] != suite["position_set_id"]
    for metric in payload["metrics"]:
        assert metric["denominator"] == suite["example_count"] - 1
    failed = [
        a
        for a in list_attempts(conn, task="benchmark_move", benchmark_run_id=payload["run_id"])
        if a["status"] == "transport_failed"
    ]
    assert len(failed) == 1
    assert failed[0]["raw_response"] is None
    assert failed[0]["reply_source"] == "live"


def test_benchmark_rejects_unknown_source_and_suite(tmp_path: Path):
    conn = make_conn(tmp_path)
    with pytest.raises(AdaptationError, match="unknown evaluation suite"):
        run_job(conn, "text.benchmark_eval", {"suite_id": "nope"}, None)
    suite = seeded_suite(conn)
    with pytest.raises(AdaptationError, match="unknown benchmark source"):
        run_job(
            conn,
            "text.benchmark_eval",
            {"suite_id": suite["id"], "source": "psychic"},
            None,
        )


def test_live_gather_holds_no_write_lock_during_network_calls(tmp_path: Path, monkeypatch):
    """Finding: the first attempt insert used to open the write
    transaction, which then stayed open across every further provider
    call. The fake provider here writes through a second real
    connection with a short busy timeout on every call; if the handler
    held SQLite's write lock while 'on the network', these writes would
    raise 'database is locked'."""
    from euro_chess_studio.data.llm_client import ChatOutcome

    db_path = tmp_path / "test.db"
    conn = get_connection(db_path)
    init_db(conn)
    seed_adaptation_fixtures(conn)
    suite = seeded_suite(conn)

    calls = {"count": 0}

    def chatty_writer(messages, *, json_response=False, timeout=None, model=None):
        calls["count"] += 1
        import sqlite3 as sqlite3_module

        other = sqlite3_module.connect(db_path, timeout=0.2)
        try:
            other.execute("PRAGMA busy_timeout = 200")
            other.execute(
                "INSERT INTO users (id, name, created_at) VALUES (?, ?, ?)",
                (f"probe_{calls['count']}", "Probe", "now"),
            )
            other.commit()
        finally:
            other.close()
        return ChatOutcome(
            content='{"move": "a2a3"}',
            model="gpt-5.6-luna",
            provider_alias="opponent",
            attempts=1,
            request_ids=(f"req-{calls['count']}",),
            json_mode_requested=True,
            json_mode_sent=True,
            json_mode_dropped=False,
            reasoning_effort_dropped=False,
        )

    monkeypatch.setattr(adaptation_handlers.llm_client, "chat", chatty_writer)
    monkeypatch.setattr(adaptation_handlers.llm_client, "get_llm_model", lambda: "gpt-5.6-luna")
    run_job(
        conn,
        "text.benchmark_eval",
        {"suite_id": suite["id"], "checkpoint": BASE_CHECKPOINT, "source": "live"},
        None,
    )
    assert calls["count"] == suite["example_count"]
    probes = conn.execute("SELECT COUNT(*) FROM users WHERE name = 'Probe'").fetchone()[0]
    assert probes == suite["example_count"]


def test_rerunning_a_benchmark_keeps_both_runs_metric_rows(tmp_path: Path):
    """Benchmark metrics are immutable history: a re-run must add its
    own rows, not replace the previous run's."""
    conn = make_conn(tmp_path)
    train(conn)
    suite = seeded_suite(conn)
    run_ids = []
    for _ in range(2):
        payload = json.loads(
            run_job(
                conn,
                "text.benchmark_eval",
                {"suite_id": suite["id"], "checkpoint": BASE_CHECKPOINT},
                None,
            ).artifact["payload_json"]
        )
        run_ids.append(payload["run_id"])
    counts = [
        conn.execute("SELECT COUNT(*) FROM eval_results WHERE run_id = ?", (run_id,)).fetchone()[0]
        for run_id in run_ids
    ]
    assert counts == [3, 3]


def test_benchmark_run_links_to_its_job_config(tmp_path: Path):
    conn = make_conn(tmp_path)
    result = run_job(
        conn,
        "text.benchmark_eval",
        {"suite_id": seeded_suite(conn)["id"], "checkpoint": BASE_CHECKPOINT},
        None,
    )
    payload = json.loads(result.artifact["payload_json"])
    run_row = conn.execute(
        "SELECT * FROM benchmark_runs WHERE id = ?", (payload["run_id"],)
    ).fetchone()
    assert run_row["job_config_id"] == result.job_config["id"]


class _FakeClock:
    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now


def test_live_run_respects_the_overall_deadline(tmp_path: Path, monkeypatch):
    """Per-example timeouts alone let twelve slow calls stack; the run
    deadline bounds the whole thing and records never-attempted
    examples as transport failures naming the reason."""
    from euro_chess_studio.data.llm_client import ChatOutcome

    conn = make_conn(tmp_path)
    suite = seeded_suite(conn)
    clock = _FakeClock()
    monkeypatch.setattr(adaptation_handlers.time, "monotonic", clock.monotonic)
    monkeypatch.setenv("BENCHMARK_RUN_DEADLINE_SECONDS", "60")

    calls = {"count": 0}

    def slow_chat(messages, *, json_response=False, timeout=None, model=None):
        calls["count"] += 1
        clock.now += 25.0
        return ChatOutcome(
            content='{"move": "a2a3"}',
            model="gpt-5.6-luna",
            provider_alias="opponent",
            attempts=1,
            request_ids=("req-x",),
            json_mode_requested=True,
            json_mode_sent=True,
            json_mode_dropped=False,
            reasoning_effort_dropped=False,
        )

    monkeypatch.setattr(adaptation_handlers.llm_client, "chat", slow_chat)
    monkeypatch.setattr(adaptation_handlers.llm_client, "get_llm_model", lambda: "gpt-5.6-luna")
    payload = json.loads(
        run_job(
            conn,
            "text.benchmark_eval",
            {"suite_id": suite["id"], "checkpoint": BASE_CHECKPOINT, "source": "live"},
            None,
        ).artifact["payload_json"]
    )
    # 60s budget at 25s per call: three calls fit, nine never start.
    assert calls["count"] == 3
    assert payload["reply_count"] == 3
    assert payload["transport_failed_count"] == suite["example_count"] - 3
    deadline_rows = conn.execute(
        "SELECT COUNT(*) FROM model_attempts WHERE benchmark_run_id = ? "
        "AND error_detail = 'run deadline exceeded'",
        (payload["run_id"],),
    ).fetchone()[0]
    assert deadline_rows == suite["example_count"] - 3


def test_live_run_aborts_after_consecutive_transport_failures(tmp_path: Path, monkeypatch):
    from euro_chess_studio.data.llm_client import LlmRequestError

    conn = make_conn(tmp_path)
    suite = seeded_suite(conn)
    calls = {"count": 0}

    def dead_provider(messages, *, json_response=False, timeout=None, model=None):
        calls["count"] += 1
        raise LlmRequestError(
            "provider unreachable", status_code=None, request_ids=(), transport_attempts=1
        )

    monkeypatch.setattr(adaptation_handlers.llm_client, "chat", dead_provider)
    monkeypatch.setattr(adaptation_handlers.llm_client, "get_llm_model", lambda: "gpt-5.6-luna")
    payload = json.loads(
        run_job(
            conn,
            "text.benchmark_eval",
            {"suite_id": suite["id"], "checkpoint": BASE_CHECKPOINT, "source": "live"},
            None,
        ).artifact["payload_json"]
    )
    # A dead provider costs three calls, not twelve.
    assert calls["count"] == 3
    assert payload["reply_count"] == 0
    aborted_rows = conn.execute(
        "SELECT COUNT(*) FROM model_attempts WHERE benchmark_run_id = ? "
        "AND error_detail LIKE 'aborted after%'",
        (payload["run_id"],),
    ).fetchone()[0]
    assert aborted_rows == suite["example_count"] - 3
