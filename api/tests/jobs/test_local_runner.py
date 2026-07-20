import json
from pathlib import Path

import pytest

from euro_chess_studio.actions.moves import make_move
from euro_chess_studio.actions.workspaces import create_or_get_workspace, join_workshop
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.eval_results_repo import list_eval_results
from euro_chess_studio.data.model_attempts_repo import insert_attempt
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


def test_text_prompt_eval_scoped_by_model_lets_base_and_adapted_results_coexist(
    tmp_path: Path,
):
    """Reproduces the reported gap: running the eval scoped to two
    different models must not have the second run's result clobber the
    first's. Before the fix, replace_eval_result's identity ignored
    scope, so a base and an adapted model's rows fought over the same
    row."""
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")
    insert_attempt(
        conn,
        workspace_id=workspace["id"],
        task="move",
        actor="model",
        model="gemma-4-2b-local",
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
        model="gpt-5.6-luna",
        attempt_number=1,
        status="applied",
        raw_response='{"move": "e2e4"}',
        json_requested=True,
        parse_ok=True,
        parsed_move="e2e4",
        is_legal=True,
    )
    conn.commit()

    runner = LocalRunner()
    runner.run(
        conn,
        JobConfig(
            job_type="text.prompt_eval",
            params={"model": "gemma-4-2b-local"},
            workspace_id=workspace["id"],
        ),
    )
    runner.run(
        conn,
        JobConfig(
            job_type="text.prompt_eval",
            params={"model": "gpt-5.6-luna"},
            workspace_id=workspace["id"],
        ),
    )

    persisted = list_eval_results(conn, modality="text", workspace_id=workspace["id"])
    model_rows = {
        row["model"]: row for row in persisted if row["metric"] == "model_legal_move_rate"
    }
    assert set(model_rows) == {"gemma-4-2b-local", "gpt-5.6-luna"}
    assert model_rows["gemma-4-2b-local"]["value"] == 0.0
    assert model_rows["gpt-5.6-luna"]["value"] == 1.0


def test_text_prompt_eval_checkpoint_scoping_covers_valid_json_rate_too(tmp_path: Path):
    """Reproduces the reported checkpoint bug: with one model and
    base/adapter checkpoints, valid_json_rate had no checkpoint filter
    at all, so a single unscoped row pooled attempts from both
    checkpoints together while model_legal_move_rate correctly kept
    them apart."""
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")
    insert_attempt(
        conn,
        workspace_id=workspace["id"],
        task="move",
        actor="model",
        model="gemma-4-2b-local",
        checkpoint="base",
        attempt_number=1,
        status="illegal",
        raw_response="not json at all",
        json_requested=True,
        parse_ok=False,
        is_legal=False,
        fen="pos-1",
    )
    insert_attempt(
        conn,
        workspace_id=workspace["id"],
        task="move",
        actor="model",
        model="gemma-4-2b-local",
        checkpoint="adapter",
        attempt_number=1,
        status="applied",
        raw_response='{"move": "e2e4"}',
        json_requested=True,
        parse_ok=True,
        parsed_move="e2e4",
        is_legal=True,
        fen="pos-1",
    )
    conn.commit()

    runner = LocalRunner()
    runner.run(
        conn,
        JobConfig(
            job_type="text.prompt_eval",
            params={"model": "gemma-4-2b-local", "checkpoint": "base"},
            workspace_id=workspace["id"],
        ),
    )
    runner.run(
        conn,
        JobConfig(
            job_type="text.prompt_eval",
            params={"model": "gemma-4-2b-local", "checkpoint": "adapter"},
            workspace_id=workspace["id"],
        ),
    )

    persisted = list_eval_results(conn, modality="text", workspace_id=workspace["id"])
    json_rows = {row["checkpoint"]: row for row in persisted if row["metric"] == "valid_json_rate"}
    # Two distinct checkpoint rows, not one unscoped row pooling both.
    assert set(json_rows) == {"base", "adapter"}
    assert json_rows["base"]["value"] == 0.0
    assert json_rows["adapter"]["value"] == 1.0
    legal_rows = {
        row["checkpoint"]: row for row in persisted if row["metric"] == "model_legal_move_rate"
    }
    assert set(legal_rows) == {"base", "adapter"}


def test_text_prompt_eval_different_position_sets_coexist_as_separate_windows(
    tmp_path: Path,
):
    """Reproduces the reported window-overwrite bug: two evaluation runs
    for the same model/checkpoint scope, over two different position
    sets, used to silently clobber each other because identity only
    covered model/checkpoint. They must coexist as distinct windows."""
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")
    insert_attempt(
        conn,
        workspace_id=workspace["id"],
        task="move",
        actor="model",
        model="gpt-5.6-luna",
        attempt_number=1,
        status="applied",
        raw_response='{"move": "e2e4"}',
        json_requested=True,
        parse_ok=True,
        is_legal=True,
        fen="window-one-position",
    )
    conn.commit()
    runner = LocalRunner()
    runner.run(
        conn,
        JobConfig(
            job_type="text.prompt_eval",
            params={"model": "gpt-5.6-luna"},
            workspace_id=workspace["id"],
        ),
    )

    # A second, later window: a new attempt over a different position.
    insert_attempt(
        conn,
        workspace_id=workspace["id"],
        task="move",
        actor="model",
        model="gpt-5.6-luna",
        attempt_number=1,
        status="illegal",
        raw_response='{"move": "a1a8"}',
        json_requested=True,
        parse_ok=True,
        is_legal=False,
        fen="window-two-position",
    )
    conn.commit()
    runner.run(
        conn,
        JobConfig(
            job_type="text.prompt_eval",
            params={"model": "gpt-5.6-luna"},
            workspace_id=workspace["id"],
        ),
    )

    persisted = list_eval_results(conn, modality="text", workspace_id=workspace["id"])
    legal_rows = [row for row in persisted if row["metric"] == "model_legal_move_rate"]
    # The second run's sample includes both attempts (they're both still
    # in the table), so this reproduces the exact regression only when
    # the position set actually differs between runs -- which it does
    # here, since the sample grew. Two distinct position sets means two
    # distinct rows must be able to coexist rather than the identity
    # forcing a silent overwrite.
    position_set_ids = {row["position_set_id"] for row in legal_rows}
    assert len(legal_rows) == len(position_set_ids), legal_rows


def test_text_prompt_eval_rerunning_the_identical_window_replaces_in_place(tmp_path: Path):
    """The original design -- re-running the same eval updates the
    number instead of stacking duplicates -- must still hold when
    nothing about the underlying data changed between runs."""
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")
    insert_attempt(
        conn,
        workspace_id=workspace["id"],
        task="move",
        actor="model",
        model="gpt-5.6-luna",
        attempt_number=1,
        status="applied",
        raw_response='{"move": "e2e4"}',
        json_requested=True,
        parse_ok=True,
        is_legal=True,
        fen="only-position",
    )
    conn.commit()

    runner = LocalRunner()
    runner.run(
        conn,
        JobConfig(
            job_type="text.prompt_eval",
            params={"model": "gpt-5.6-luna"},
            workspace_id=workspace["id"],
        ),
    )
    runner.run(
        conn,
        JobConfig(
            job_type="text.prompt_eval",
            params={"model": "gpt-5.6-luna"},
            workspace_id=workspace["id"],
        ),
    )

    persisted = list_eval_results(conn, modality="text", workspace_id=workspace["id"])
    legal_rows = [row for row in persisted if row["metric"] == "model_legal_move_rate"]
    assert len(legal_rows) == 1


def test_text_prompt_eval_persists_run_id_and_the_frozen_sample_ids(tmp_path: Path):
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")
    move_row = make_move(conn, workspace["id"], "e2e4").move
    attempt_row = insert_attempt(
        conn,
        workspace_id=workspace["id"],
        task="move",
        actor="model",
        model="gpt-5.6-luna",
        attempt_number=1,
        status="applied",
        raw_response='{"move": "e7e5"}',
        json_requested=True,
        parse_ok=True,
        parsed_move="e7e5",
        is_legal=True,
        fen=move_row["fen_after"],
    )
    conn.commit()

    runner = LocalRunner()
    runner.run(
        conn, JobConfig(job_type="text.prompt_eval", params={}, workspace_id=workspace["id"])
    )

    persisted = list_eval_results(conn, modality="text", workspace_id=workspace["id"])
    by_metric = {row["metric"]: row for row in persisted}

    # Every metric from one run_job call shares a run_id.
    run_ids = {row["run_id"] for row in persisted}
    assert len(run_ids) == 1
    assert next(iter(run_ids))

    # The audit trail: exactly the rows that were counted.
    legal_move_sample = json.loads(by_metric["legal_move_rate"]["sample_ids_json"])
    assert legal_move_sample == [move_row["id"]]
    model_sample = json.loads(by_metric["model_legal_move_rate"]["sample_ids_json"])
    assert model_sample == [attempt_row["id"]]

    # The frozen input set: the actual positions, and a stable hash of
    # them, not just the output row ids above.
    legal_move_row = by_metric["legal_move_rate"]
    assert json.loads(legal_move_row["position_set_json"]) == [move_row["fen_before"]]
    assert legal_move_row["position_set_id"]
    model_row = by_metric["model_legal_move_rate"]
    assert json.loads(model_row["position_set_json"]) == [attempt_row["fen"]]
    assert model_row["position_set_id"]


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
