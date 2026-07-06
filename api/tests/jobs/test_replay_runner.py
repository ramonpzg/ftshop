from pathlib import Path

import pytest

from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.jobs.base import JobConfig
from euro_chess_studio.jobs.replay_runner import FixtureNotFoundError, ReplayRunner


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    return conn


def test_replay_runner_loads_image_show_dataset_fixture(tmp_path: Path):
    conn = make_conn(tmp_path)
    runner = ReplayRunner()
    output = runner.run(
        conn, JobConfig(job_type="image.show_dataset", params={}, workspace_id=None)
    )
    assert output.modality == "image"
    assert len(output.payload["rows"]) > 0


def test_replay_runner_loads_reveal_cached_fixture(tmp_path: Path):
    conn = make_conn(tmp_path)
    runner = ReplayRunner()
    output = runner.run(
        conn,
        JobConfig(
            job_type="artifact.reveal_cached",
            params={"modality": "audio", "key": "board_sound"},
            workspace_id=None,
        ),
    )
    assert output.modality == "audio"
    assert output.payload["event"] == "capture"


def test_replay_runner_rejects_reveal_cached_without_params(tmp_path: Path):
    conn = make_conn(tmp_path)
    runner = ReplayRunner()
    with pytest.raises(FixtureNotFoundError):
        runner.run(conn, JobConfig(job_type="artifact.reveal_cached", params={}, workspace_id=None))


def test_replay_runner_rejects_unknown_job_type(tmp_path: Path):
    conn = make_conn(tmp_path)
    runner = ReplayRunner()
    with pytest.raises(FixtureNotFoundError):
        runner.run(conn, JobConfig(job_type="not.a.job", params={}, workspace_id=None))


def test_replay_runner_rejects_missing_fixture_file(tmp_path: Path):
    conn = make_conn(tmp_path)
    runner = ReplayRunner()
    with pytest.raises(FixtureNotFoundError):
        runner.run(
            conn,
            JobConfig(
                job_type="artifact.reveal_cached",
                params={"modality": "text", "key": "does-not-exist"},
                workspace_id=None,
            ),
        )


def test_replay_runner_rejects_path_traversal_segments(tmp_path: Path):
    conn = make_conn(tmp_path)
    runner = ReplayRunner()
    for modality, key in [("..", "secrets"), ("text", "../../pyproject"), ("a/b", "x")]:
        with pytest.raises(FixtureNotFoundError):
            runner.run(
                conn,
                JobConfig(
                    job_type="artifact.reveal_cached",
                    params={"modality": modality, "key": key},
                    workspace_id=None,
                ),
            )
