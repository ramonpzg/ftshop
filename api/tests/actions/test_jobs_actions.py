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


def test_run_job_validates_the_workspace_before_the_runner_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Identity before work: a bad workspace id must fail on a plain
    read, not trigger provider work or file output first and then trip
    the config row's foreign key."""
    from euro_chess_studio.actions import jobs as jobs_action
    from euro_chess_studio.actions.errors import WorkspaceNotFoundError

    conn = make_conn(tmp_path)
    runner_calls: list[str] = []

    class SpyRunner:
        def run(self, conn, job):
            runner_calls.append(job.job_type)
            raise AssertionError("the runner must not run for an unknown workspace")

    monkeypatch.setattr(jobs_action, "get_runner_for_job_type", lambda job_type: SpyRunner())

    with pytest.raises(WorkspaceNotFoundError, match="unknown workspace"):
        run_job(conn, "image.show_dataset", {}, "nope")

    assert runner_calls == []
    assert conn.execute("SELECT COUNT(*) FROM job_configs").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0


def test_run_job_commits_config_and_artifact_together_or_neither(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Reproduces the reported bug: a failure while persisting the
    artifact must not leave a committed job_config with no matching
    artifact. Verified from a second connection, since the same
    connection would see its own uncommitted writes either way."""
    from euro_chess_studio.actions import jobs as jobs_action

    conn = make_conn(tmp_path)
    conn.commit()

    def explode(*args, **kwargs):
        raise RuntimeError("simulated artifact failure")

    monkeypatch.setattr(jobs_action, "insert_artifact", explode)
    with pytest.raises(RuntimeError, match="simulated"):
        run_job(conn, "audio.make_spectrogram", {"duration_seconds": 0.4}, None)

    other = get_connection(tmp_path / "test.db")
    try:
        assert other.execute("SELECT COUNT(*) FROM job_configs").fetchone()[0] == 0
        assert other.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0
    finally:
        other.close()


def test_run_job_rolls_back_eval_results_when_the_artifact_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """text.prompt_eval writes eval_results as a side effect of the
    handler; those writes must roll back with the rest of the job if
    persisting the artifact afterward fails, not survive as orphaned
    numbers with no artifact to show for them."""
    from euro_chess_studio.actions import jobs as jobs_action
    from euro_chess_studio.actions.moves import make_move
    from euro_chess_studio.actions.workspaces import create_or_get_workspace, join_workshop
    from euro_chess_studio.calculations.pages import PAGES
    from euro_chess_studio.data.pages_repo import upsert_page

    conn = make_conn(tmp_path)
    for page in PAGES:
        upsert_page(conn, page)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")
    make_move(conn, workspace["id"], "e2e4")
    conn.commit()

    def explode(*args, **kwargs):
        raise RuntimeError("simulated artifact failure")

    monkeypatch.setattr(jobs_action, "insert_artifact", explode)
    with pytest.raises(RuntimeError, match="simulated"):
        run_job(conn, "text.prompt_eval", {}, workspace["id"])

    other = get_connection(tmp_path / "test.db")
    try:
        assert other.execute("SELECT COUNT(*) FROM eval_results").fetchone()[0] == 0
    finally:
        other.close()
