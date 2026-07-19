from pathlib import Path

import pytest

from euro_chess_studio.actions.moves import make_move
from euro_chess_studio.actions.workspaces import create_or_get_workspace, join_workshop
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.eval_results_repo import list_eval_results
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.jobs.base import JobConfig
from euro_chess_studio.jobs.local_runner import LocalRunner, UnknownJobTypeError


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    for page in PAGES:
        upsert_page(conn, page)
    return conn


def test_text_prompt_eval_separates_participant_and_model_metrics(tmp_path: Path):
    from euro_chess_studio.data.model_attempts_repo import insert_attempt

    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")
    # Participant: two legal, one illegal.
    make_move(conn, workspace["id"], "e2e4")
    make_move(conn, workspace["id"], "e7e6")
    make_move(conn, workspace["id"], "e2e5")  # illegal (already moved)
    # Model: one illegal reply, one non-JSON reply, one applied move.
    insert_attempt(
        conn,
        workspace_id=workspace["id"],
        task="move",
        actor="model",
        attempt_number=1,
        status="illegal",
        raw_response='{"move": "a1a8"}',
        json_requested=True,
        parse_ok=True,
        parsed_move="a1a8",
        is_legal=False,
    )
    insert_attempt(
        conn,
        workspace_id=workspace["id"],
        task="move",
        actor="model",
        attempt_number=2,
        status="parse_failed",
        raw_response="I would castle early.",
        json_requested=True,
    )
    insert_attempt(
        conn,
        workspace_id=workspace["id"],
        task="move",
        actor="model",
        attempt_number=3,
        status="applied",
        raw_response='{"move": "d2d4"}',
        json_requested=True,
        parse_ok=True,
        parsed_move="d2d4",
        is_legal=True,
    )
    conn.commit()

    runner = LocalRunner()
    output = runner.run(
        conn, JobConfig(job_type="text.prompt_eval", params={}, workspace_id=workspace["id"])
    )

    assert output.modality == "text"
    assert output.payload["move_count"] == 3
    assert output.payload["model_attempt_count"] == 3
    metrics = {entry["metric"]: entry for entry in output.payload["metrics"]}
    # Participant moves never count for the model and vice versa.
    assert metrics["legal_move_rate"]["value"] == pytest.approx(2 / 3)
    assert metrics["legal_move_rate"]["scope"] == {"actor": "participant"}
    assert metrics["model_legal_move_rate"]["value"] == pytest.approx(1 / 3)
    assert metrics["model_legal_move_rate"]["denominator"] == 3
    # The non-JSON reply lowers valid_json_rate, measured on raw replies.
    assert metrics["valid_json_rate"]["value"] == pytest.approx(2 / 3)

    persisted = list_eval_results(conn, modality="text", workspace_id=workspace["id"])
    by_metric = {row["metric"]: row for row in persisted}
    stored = by_metric["model_legal_move_rate"]
    assert stored["numerator"] == 1
    assert stored["denominator"] == 3
    assert stored["direction"] == "higher_is_better"
    assert '"actor": "model"' in stored["scope_json"]
    assert stored["definition"]


def test_text_prompt_eval_with_no_data_reports_unavailable_and_persists_nothing(
    tmp_path: Path,
):
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")

    runner = LocalRunner()
    output = runner.run(
        conn, JobConfig(job_type="text.prompt_eval", params={}, workspace_id=workspace["id"])
    )

    for entry in output.payload["metrics"]:
        assert entry["available"] is False
        assert entry["value"] is None
    assert list_eval_results(conn, modality="text", workspace_id=workspace["id"]) == []


def test_text_reward_eval_sums_real_rewards(tmp_path: Path):
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")
    make_move(conn, workspace["id"], "e2e4")

    runner = LocalRunner()
    output = runner.run(
        conn, JobConfig(job_type="text.reward_eval", params={}, workspace_id=workspace["id"])
    )
    assert output.payload["total_reward"] == 1
    assert len(output.payload["rewards"]) == 1


def test_audio_make_spectrogram_returns_a_grid(tmp_path: Path):
    conn = make_conn(tmp_path)
    runner = LocalRunner()
    output = runner.run(
        conn,
        JobConfig(
            job_type="audio.make_spectrogram",
            params={"duration_seconds": 0.4, "tags": ["capture"]},
            workspace_id=None,
        ),
    )
    assert output.modality == "audio"
    assert len(output.payload["spectrogram"]) > 0


def test_video_sample_frames_returns_indices(tmp_path: Path):
    conn = make_conn(tmp_path)
    runner = LocalRunner()
    output = runner.run(
        conn,
        JobConfig(
            job_type="video.sample_frames",
            params={"total_frames": 100, "fps": 25, "num_samples": 4},
            workspace_id=None,
        ),
    )
    assert output.payload["sampled_indices"] == [0, 25, 50, 75]


def test_local_runner_rejects_unknown_job_type(tmp_path: Path):
    conn = make_conn(tmp_path)
    runner = LocalRunner()
    with pytest.raises(UnknownJobTypeError):
        runner.run(conn, JobConfig(job_type="not.a.job", params={}, workspace_id=None))
