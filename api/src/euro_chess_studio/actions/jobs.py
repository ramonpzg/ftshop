"""Action: run a job. Persists the job config and the resulting artifact."""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from euro_chess_studio.actions.errors import JobInProgressError, WorkspaceNotFoundError
from euro_chess_studio.calculations.generation import SingleFlightLock, single_flight_lock
from euro_chess_studio.calculations.ids import generate_id
from euro_chess_studio.data.artifacts_repo import insert_artifact
from euro_chess_studio.data.job_configs_repo import insert_job_config
from euro_chess_studio.data.run_locks_repo import delete_lock, get_lock, insert_lock
from euro_chess_studio.data.workspaces_repo import get_workspace
from euro_chess_studio.jobs.base import JobConfig
from euro_chess_studio.jobs.registry import get_runner_for_job_type


@dataclass(frozen=True)
class RunJobResult:
    job_config: sqlite3.Row
    artifact: sqlite3.Row


def _acquire_single_flight(conn: sqlite3.Connection, lock: SingleFlightLock) -> None:
    """Commits the in-progress row before any work happens, so a second
    request -- another tab, a reloaded panel -- sees it immediately and
    is refused instead of trusted to remember. A row past its expiry is
    a crashed run's leftovers and is replaced, not honored. The primary
    key stays the arbiter if two requests race past the read."""
    now = datetime.now(UTC)
    existing = get_lock(conn, lock.key)
    if existing is not None:
        expires_at = datetime.fromisoformat(existing["expires_at"])
        if expires_at > now:
            remaining = (expires_at - now).total_seconds()
            raise JobInProgressError(
                f"a run of {lock.key.split(':')[0]} is already in progress; "
                "it lands in the run list or times out within "
                f"{remaining:.0f} seconds"
            )
        delete_lock(conn, lock.key)
    try:
        insert_lock(
            conn,
            lock.key,
            acquired_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=lock.ttl_seconds)).isoformat(),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise JobInProgressError(
            f"a run of {lock.key.split(':')[0]} is already in progress; "
            "another request started it just now"
        ) from exc


def _release_single_flight(conn: sqlite3.Connection, lock: SingleFlightLock) -> None:
    delete_lock(conn, lock.key)
    conn.commit()


def run_job(
    conn: sqlite3.Connection,
    job_type: str,
    params: dict,
    workspace_id: str | None,
) -> RunJobResult:
    runner = get_runner_for_job_type(job_type)  # raises UnknownJobTypeError if invalid

    # Identity before work: the runner may spend provider money or write
    # files, and the config insert below would only reject a bad
    # workspace afterwards (foreign key), when the spend has already
    # happened. A plain read needs no write lock.
    if workspace_id is not None and get_workspace(conn, workspace_id) is None:
        raise WorkspaceNotFoundError(f"unknown workspace: {workspace_id}")

    # Single-flight identity before work, for the same reason: a
    # duplicate live benchmark is money spent twice for one answer, and
    # only a durable, committed record can refuse it across reloads and
    # tabs. React state cannot; it dies with the tab.
    lock = single_flight_lock(job_type, params)
    if lock is not None:
        _acquire_single_flight(conn, lock)

    # Run first, persist after: a failed generation (missing API key,
    # provider error) must not leave an orphaned config row behind, and
    # a handler that talks to the network before its first write (the
    # live benchmark gathers every reply up front) must not do so with
    # SQLite's write lock already held by a config insert. The config id
    # is generated up front so handlers can link durable records to the
    # configuration that produced them; the row itself lands after the
    # runner, inside the same transaction, so the link and the config
    # commit together or not at all. Config, artifact, and everything
    # the handler wrote (no repo on this path commits) rise or fall
    # together.
    job_config_id = generate_id("job")
    try:
        output = runner.run(
            conn,
            JobConfig(
                job_type=job_type,
                params=params,
                workspace_id=workspace_id,
                job_config_id=job_config_id,
            ),
        )
        job_config_row = insert_job_config(
            conn,
            workspace_id=workspace_id,
            job_type=job_type,
            params=params,
            job_config_id=job_config_id,
        )
        artifact_row = insert_artifact(
            conn,
            job_config_id=job_config_row["id"],
            modality=output.modality,
            kind=output.kind,
            payload=output.payload,
            cached=output.cached,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        # The lock row was committed separately, so it survives the
        # rollback above and must be released on both paths. A process
        # that dies here leaves the row to expire on its own.
        if lock is not None:
            _release_single_flight(conn, lock)
    return RunJobResult(job_config=job_config_row, artifact=artifact_row)
