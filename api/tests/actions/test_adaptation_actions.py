"""Tests for the adaptation actions: freezing a snapshot from real room
play (through the real make_move path), fixture seeding idempotency,
and the assembled panel state including the comparison."""

import json
from pathlib import Path

import chess
import pytest

from euro_chess_studio.actions.adaptation import (
    freeze_dataset_snapshot,
    get_adaptation_state,
    seed_adaptation_fixtures,
)
from euro_chess_studio.actions.jobs import run_job
from euro_chess_studio.actions.moves import make_move
from euro_chess_studio.calculations.adaptation import AdaptationError
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.users_repo import insert_user
from euro_chess_studio.data.workspaces_repo import insert_workspace

STARTING_FEN = chess.STARTING_FEN


def make_workspace(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    for page in PAGES:
        upsert_page(conn, page)
    page = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    user = insert_user(conn, "Ada")
    workspace = insert_workspace(
        conn, "workspace_1", user["id"], page["id"], "shape:1", STARTING_FEN
    )
    conn.commit()
    return conn, workspace


def test_seeding_is_idempotent_by_content_hash(tmp_path: Path):
    conn, _ = make_workspace(tmp_path)
    assert seed_adaptation_fixtures(conn) == 2
    assert seed_adaptation_fixtures(conn) == 0
    state = get_adaptation_state(conn)
    assert len(state["snapshots"]) == 1
    assert len(state["suites"]) == 1
    assert state["snapshots"][0]["origin"] == "seeded"
    assert state["snapshots"][0]["row_count"] == 24


def test_freeze_refuses_an_empty_room(tmp_path: Path):
    conn, _ = make_workspace(tmp_path)
    with pytest.raises(AdaptationError, match="no training-eligible rows"):
        freeze_dataset_snapshot(conn)


def test_freeze_excludes_fallback_moves_and_hashes_content(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    make_move(conn, workspace["id"], "e2e4", actor="participant")
    make_move(conn, workspace["id"], "e7e5", actor="model", model="gemma-4-2b-local")
    make_move(conn, workspace["id"], "a2a3", actor="fallback", model="gemma-4-2b-local")

    snapshot = freeze_dataset_snapshot(conn)
    assert snapshot["origin"] == "frozen"
    assert snapshot["row_count"] == 2
    assert snapshot["excluded_ineligible_count"] == 1
    assert snapshot["source_workspace_count"] == 1
    rows = json.loads(snapshot["rows_json"])
    assert len(rows) == 2
    # The fallback move's position (after e4 e5) never enters the rows.
    assert all("a2a3" not in row["completion"] for row in rows)
    assert snapshot["content_hash"]

    # The same room data freezes to the same content hash.
    second = freeze_dataset_snapshot(conn)
    assert second["content_hash"] == snapshot["content_hash"]
    assert second["label"] != snapshot["label"]


def test_freeze_counts_raw_and_approved_scenarios_separately(tmp_path: Path):
    from euro_chess_studio.data.scenario_repo import insert_scenario, set_review

    conn, workspace = make_workspace(tmp_path)
    make_move(conn, workspace["id"], "e2e4", actor="participant")
    insert_scenario(
        conn,
        workspace_id=workspace["id"],
        ply=1,
        fen=STARTING_FEN,
        status="suggested",
        suggested_assessment="even",
        suggested_real_world="a negotiation opens",
        suggested_video_prompt="a meeting room scene",
        model="gpt-5.6-luna",
        provider_alias="video_prompt",
        prompt_version="assess-v1",
    )
    reviewed = insert_scenario(
        conn,
        workspace_id=workspace["id"],
        ply=2,
        fen=STARTING_FEN,
        status="suggested",
        suggested_assessment="sharp",
        suggested_real_world="a deadline lands",
        suggested_video_prompt="an office scene",
        model="gpt-5.6-luna",
        provider_alias="video_prompt",
        prompt_version="assess-v1",
    )
    set_review(
        conn,
        reviewed["id"],
        status="accepted",
        final_assessment="sharp",
        final_real_world="a deadline lands",
        final_video_prompt="an office scene",
    )
    conn.commit()

    snapshot = freeze_dataset_snapshot(conn)
    assert snapshot["scenario_raw_count"] == 2
    assert snapshot["scenario_approved_count"] == 1


def test_state_has_no_comparison_until_both_runs_exist(tmp_path: Path):
    conn, _ = make_workspace(tmp_path)
    seed_adaptation_fixtures(conn)
    state = get_adaptation_state(conn)
    assert state["comparison"] is None

    snapshot = state["snapshots"][0]
    suite = state["suites"][0]
    run_job(
        conn,
        "text.train_adapter",
        {"dataset_snapshot_id": snapshot["id"], "config_id": "text-gemma-lora-v1"},
        None,
    )
    run_job(conn, "text.benchmark_eval", {"suite_id": suite["id"], "checkpoint": "base"}, None)
    state = get_adaptation_state(conn)
    assert state["comparison"] is None

    run_job(
        conn,
        "text.benchmark_eval",
        {"suite_id": suite["id"], "checkpoint": "gemma-chess-sft-v1"},
        None,
    )
    state = get_adaptation_state(conn)
    comparison = state["comparison"]
    assert comparison is not None
    assert comparison["comparable"] is True
    by_metric = {m["metric"]: m for m in comparison["metrics"]}
    assert by_metric["model_legal_move_rate"]["verdict"] == "improved"
    assert by_metric["explanation_rate"]["verdict"] == "regressed"
    assert len(comparison["examples"]) == suite["example_count"]
    # Runs and adapters are visible with their provenance.
    assert len(state["runs"]) == 2
    assert len(state["adapters"]) == 1
    assert state["adapters"][0]["dataset_content_hash"] == snapshot["content_hash"]


def test_replay_with_a_missing_reply_fails_loudly(tmp_path: Path, monkeypatch):
    """A fixture missing one example's reply must refuse the whole run
    rather than silently benchmark eleven twelfths of the suite."""
    from euro_chess_studio.jobs import adaptation_handlers

    conn, _ = make_workspace(tmp_path)
    seed_adaptation_fixtures(conn)
    state = get_adaptation_state(conn)
    suite = state["suites"][0]

    fixture = json.loads(json.dumps(adaptation_handlers.load_benchmark_replies_fixture()))
    first_example = next(iter(fixture["checkpoints"]["base"]["replies"]))
    del fixture["checkpoints"]["base"]["replies"][first_example]
    monkeypatch.setattr(adaptation_handlers, "load_benchmark_replies_fixture", lambda: fixture)
    with pytest.raises(AdaptationError, match="no reply for example"):
        run_job(conn, "text.benchmark_eval", {"suite_id": suite["id"], "checkpoint": "base"}, None)


def _fake_chat(*, answer_model: str, fail_first: bool = False):
    """A chat double answering as `answer_model`, optionally failing the
    first call."""
    from euro_chess_studio.data.llm_client import ChatOutcome, LlmRequestError

    calls = {"count": 0}

    def chat(messages, *, json_response=False, timeout=None, model=None):
        calls["count"] += 1
        if fail_first and calls["count"] == 1:
            raise LlmRequestError(
                "provider unreachable", status_code=None, request_ids=(), transport_attempts=3
            )
        return ChatOutcome(
            content='{"move": "a2a3"}',
            model=answer_model,
            provider_alias="opponent",
            attempts=1,
            request_ids=("req-x",),
            json_mode_requested=True,
            json_mode_sent=True,
            json_mode_dropped=False,
            reasoning_effort_dropped=False,
        )

    return chat


def test_mismatched_position_sets_refuse_deltas_end_to_end(tmp_path: Path, monkeypatch):
    """A live base run with one transport failure measured a smaller
    position set than the replayed adapted run; the assembled comparison
    must refuse every delta with the position-set reason. The live
    endpoint here serves the adapter's own base model (the properly
    configured local path), so the refusal is about the window, not the
    lineage."""
    from euro_chess_studio.jobs import adaptation_handlers

    conn, _ = make_workspace(tmp_path)
    seed_adaptation_fixtures(conn)
    state = get_adaptation_state(conn)
    snapshot = state["snapshots"][0]
    suite = state["suites"][0]
    run_job(
        conn,
        "text.train_adapter",
        {"dataset_snapshot_id": snapshot["id"], "config_id": "text-gemma-lora-v1"},
        None,
    )

    monkeypatch.setattr(
        adaptation_handlers.llm_client,
        "chat",
        _fake_chat(answer_model="gemma-4-2b-local", fail_first=True),
    )
    monkeypatch.setattr(adaptation_handlers.llm_client, "get_llm_model", lambda: "gemma-4-2b-local")
    run_job(
        conn,
        "text.benchmark_eval",
        {"suite_id": suite["id"], "checkpoint": "base", "source": "live"},
        None,
    )
    run_job(
        conn,
        "text.benchmark_eval",
        {"suite_id": suite["id"], "checkpoint": "gemma-chess-sft-v1"},
        None,
    )

    comparison = get_adaptation_state(conn)["comparison"]
    assert comparison is not None
    # Run-level identities match (same suite, contract, and lineage)...
    assert comparison["comparable"] is True
    # ...but every metric refuses its delta: the windows differ.
    for metric in comparison["metrics"]:
        assert metric["comparable"] is False
        assert "different position sets" in metric["reason"]
        assert metric["delta"] is None


def test_a_live_run_of_another_model_is_not_a_fine_tuning_pair(tmp_path: Path, monkeypatch):
    """The reviewed reproduction: a gpt-5.6-luna live base run used to
    receive valid deltas against the replayed gemma adapter. Same suite,
    same prompt contract, different model -- the comparison must refuse
    at run level, every metric carrying the reason."""
    from euro_chess_studio.jobs import adaptation_handlers

    conn, _ = make_workspace(tmp_path)
    seed_adaptation_fixtures(conn)
    state = get_adaptation_state(conn)
    snapshot = state["snapshots"][0]
    suite = state["suites"][0]
    run_job(
        conn,
        "text.train_adapter",
        {"dataset_snapshot_id": snapshot["id"], "config_id": "text-gemma-lora-v1"},
        None,
    )
    monkeypatch.setattr(
        adaptation_handlers.llm_client, "chat", _fake_chat(answer_model="gpt-5.6-luna")
    )
    monkeypatch.setattr(adaptation_handlers.llm_client, "get_llm_model", lambda: "gpt-5.6-luna")
    run_job(
        conn,
        "text.benchmark_eval",
        {"suite_id": suite["id"], "checkpoint": "base", "source": "live"},
        None,
    )
    run_job(
        conn,
        "text.benchmark_eval",
        {"suite_id": suite["id"], "checkpoint": "gemma-chess-sft-v1"},
        None,
    )

    comparison = get_adaptation_state(conn)["comparison"]
    assert comparison is not None
    assert comparison["comparable"] is False
    assert any("different models" in reason for reason in comparison["reasons"])
    assert all(not metric["comparable"] for metric in comparison["metrics"])
    # Both values stay visible; the refusal is the result.
    by_metric = {m["metric"]: m for m in comparison["metrics"]}
    assert by_metric["model_legal_move_rate"]["base_value"] is not None


def test_a_newer_live_run_of_another_model_does_not_displace_the_honest_pair(
    tmp_path: Path, monkeypatch
):
    """Selection prefers the lineage-matching base run: after an honest
    replayed pair exists, a newer luna live run must not hijack the
    comparison into a refusal."""
    from euro_chess_studio.jobs import adaptation_handlers

    conn, _ = make_workspace(tmp_path)
    seed_adaptation_fixtures(conn)
    state = get_adaptation_state(conn)
    snapshot = state["snapshots"][0]
    suite = state["suites"][0]
    run_job(
        conn,
        "text.train_adapter",
        {"dataset_snapshot_id": snapshot["id"], "config_id": "text-gemma-lora-v1"},
        None,
    )
    run_job(conn, "text.benchmark_eval", {"suite_id": suite["id"], "checkpoint": "base"}, None)
    run_job(
        conn,
        "text.benchmark_eval",
        {"suite_id": suite["id"], "checkpoint": "gemma-chess-sft-v1"},
        None,
    )
    monkeypatch.setattr(
        adaptation_handlers.llm_client, "chat", _fake_chat(answer_model="gpt-5.6-luna")
    )
    monkeypatch.setattr(adaptation_handlers.llm_client, "get_llm_model", lambda: "gpt-5.6-luna")
    run_job(
        conn,
        "text.benchmark_eval",
        {"suite_id": suite["id"], "checkpoint": "base", "source": "live"},
        None,
    )

    comparison = get_adaptation_state(conn)["comparison"]
    assert comparison is not None
    assert comparison["comparable"] is True
    assert comparison["base_run"]["model"] == "gemma-4-2b-local"
    assert comparison["base_run"]["source"] == "replayed"
    # The luna run still exists as its own evidence in the run list.
    assert len(get_adaptation_state(conn)["runs"]) == 3


def test_an_obsolete_contract_suite_never_presents_as_the_benchmark(tmp_path: Path):
    """The upgraded-database reproduction: a phase-34-original sft-v1
    suite (with its old runs) must not be the primary suite, and its
    stale comparison must not resurface just because the current suite
    has no runs yet."""
    from euro_chess_studio.data.benchmark_runs_repo import insert_run
    from euro_chess_studio.data.eval_suites_repo import insert_suite

    conn, _ = make_workspace(tmp_path)
    old_suite = insert_suite(
        conn,
        label="held-out-mid-openings-v1",
        modality="text",
        origin="seeded",
        prompt_version="sft-v1",
        schema_version="suite-v1",
        example_count=1,
        content_hash="oldcontenthash00",
        position_set_id="oldpsid000000000",
        examples=[
            {
                "example_id": "old-01",
                "fen": STARTING_FEN,
                "legal_moves": ["e2e4"],
                "prompt": "old contract prompt",
            }
        ],
    )
    for checkpoint in ("base", "gemma-chess-sft-v1"):
        insert_run(
            conn,
            run_id=f"benchrun_old_{checkpoint}",
            suite_id=old_suite["id"],
            suite_content_hash=old_suite["content_hash"],
            prompt_version="sft-v1",
            checkpoint=checkpoint,
            model="gemma-4-2b-local",
            provider_alias="fixture",
            source="replayed",
            example_count=1,
            reply_count=1,
            transport_failed_count=0,
            position_set_id="oldpsid000000000",
        )
    conn.commit()
    seed_adaptation_fixtures(conn)

    state = get_adaptation_state(conn)
    assert len(state["suites"]) == 2
    assert state["suites"][0]["current_contract"] is True
    assert state["suites"][0]["prompt_version"] != "sft-v1"
    assert state["suites"][1]["current_contract"] is False
    # The old pair of runs would have produced a comparison under the
    # first-suite-with-a-comparison rule; the primary suite has no runs,
    # so there is honestly nothing to compare yet.
    assert state["comparison"] is None
