from pathlib import Path

import pytest

from euro_chess_studio.actions.jobs import run_job
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.jobs.registry import UnknownJobTypeError


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    return conn


def test_run_job_persists_job_config_and_artifact(tmp_path: Path):
    conn = make_conn(tmp_path)
    result = run_job(
        conn,
        "audio.make_spectrogram",
        {"duration_seconds": 0.4, "tags": ["capture"]},
        None,
    )
    assert result.job_config["job_type"] == "audio.make_spectrogram"
    assert result.artifact["modality"] == "audio"
    assert result.artifact["cached"] == 0


def test_run_job_marks_replay_artifacts_as_cached(tmp_path: Path):
    conn = make_conn(tmp_path)
    result = run_job(conn, "image.show_dataset", {}, None)
    assert result.artifact["cached"] == 1


def test_run_job_links_artifact_to_job_config(tmp_path: Path):
    conn = make_conn(tmp_path)
    result = run_job(conn, "video.sample_frames", {}, None)
    assert result.artifact["job_config_id"] == result.job_config["id"]


def test_run_job_rejects_unknown_job_type(tmp_path: Path):
    conn = make_conn(tmp_path)
    with pytest.raises(UnknownJobTypeError):
        run_job(conn, "not.a.job", {}, None)
