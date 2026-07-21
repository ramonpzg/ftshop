from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from euro_chess_studio.actions.errors import JobInProgressError
from euro_chess_studio.actions.jobs import run_job
from euro_chess_studio.calculations.generation import LIVE_BENCHMARK_LOCK_KEY, single_flight_lock
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.run_locks_repo import get_lock, insert_lock
from euro_chess_studio.jobs.base import JobOutput
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


def _live_params() -> dict:
    return {"suite_id": "suite-x", "checkpoint": "base", "source": "live"}


class StubRunner:
    """Stands in for the live benchmark runner: what is under test here
    is run_job's single-flight handling, not the provider calls."""

    def __init__(self):
        self.calls = 0

    def run(self, conn, job):
        self.calls += 1
        return JobOutput(modality="text", kind="benchmark_eval", cached=False, payload={"ok": True})


def test_a_live_benchmark_refuses_to_start_while_one_is_in_flight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The duplicate-run guard is durable and server-side: the committed
    in-progress row refuses a second request whatever any browser tab
    remembers. UI state alone cannot enforce this; a reloaded panel
    starts with empty state and would happily spend the money again."""
    from euro_chess_studio.actions import jobs as jobs_action

    conn = make_conn(tmp_path)
    now = datetime.now(UTC)
    insert_lock(
        conn,
        LIVE_BENCHMARK_LOCK_KEY,
        acquired_at=now.isoformat(),
        expires_at=(now + timedelta(seconds=60)).isoformat(),
    )
    conn.commit()

    runner = StubRunner()
    monkeypatch.setattr(jobs_action, "get_runner_for_job_type", lambda job_type: runner)

    with pytest.raises(JobInProgressError, match="already in progress"):
        run_job(conn, "text.benchmark_eval", _live_params(), None)
    assert runner.calls == 0
    # The refusal must not release the in-flight run's own lock.
    assert get_lock(conn, LIVE_BENCHMARK_LOCK_KEY) is not None


def test_the_live_lock_is_released_on_success_and_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from euro_chess_studio.actions import jobs as jobs_action

    conn = make_conn(tmp_path)
    runner = StubRunner()
    monkeypatch.setattr(jobs_action, "get_runner_for_job_type", lambda job_type: runner)

    run_job(conn, "text.benchmark_eval", _live_params(), None)
    assert runner.calls == 1
    assert get_lock(conn, LIVE_BENCHMARK_LOCK_KEY) is None

    class ExplodingRunner:
        def run(self, conn, job):
            raise RuntimeError("provider blew up mid-run")

    monkeypatch.setattr(jobs_action, "get_runner_for_job_type", lambda job_type: ExplodingRunner())
    with pytest.raises(RuntimeError, match="mid-run"):
        run_job(conn, "text.benchmark_eval", _live_params(), None)
    # A failed run must not leave the room locked out of live runs.
    assert get_lock(conn, LIVE_BENCHMARK_LOCK_KEY) is None


def test_an_expired_live_lock_is_replaced_not_honored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A process that died mid-run cannot release its lock. The expiry
    (the server's maximum run deadline plus slack) is what keeps a
    crash from locking live runs out until someone deletes a row by
    hand."""
    from euro_chess_studio.actions import jobs as jobs_action

    conn = make_conn(tmp_path)
    now = datetime.now(UTC)
    insert_lock(
        conn,
        LIVE_BENCHMARK_LOCK_KEY,
        acquired_at=(now - timedelta(seconds=700)).isoformat(),
        expires_at=(now - timedelta(seconds=10)).isoformat(),
    )
    conn.commit()

    runner = StubRunner()
    monkeypatch.setattr(jobs_action, "get_runner_for_job_type", lambda job_type: runner)
    run_job(conn, "text.benchmark_eval", _live_params(), None)
    assert runner.calls == 1
    assert get_lock(conn, LIVE_BENCHMARK_LOCK_KEY) is None


def test_only_live_benchmarks_are_single_flight():
    """Replays are free and may run concurrently; the lock exists for
    provider spend, nothing else."""
    assert single_flight_lock("text.benchmark_eval", {"source": "live"}) is not None
    assert single_flight_lock("text.benchmark_eval", {"source": "replayed"}) is None
    assert single_flight_lock("text.benchmark_eval", {}) is None
    assert single_flight_lock("image.show_dataset", {}) is None


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
