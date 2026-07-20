"""Action: run a job. Persists the job config and the resulting artifact."""

import sqlite3
from dataclasses import dataclass

from euro_chess_studio.actions.errors import WorkspaceNotFoundError
from euro_chess_studio.calculations.ids import generate_id
from euro_chess_studio.data.artifacts_repo import insert_artifact
from euro_chess_studio.data.job_configs_repo import insert_job_config
from euro_chess_studio.data.workspaces_repo import get_workspace
from euro_chess_studio.jobs.base import JobConfig
from euro_chess_studio.jobs.registry import get_runner_for_job_type


@dataclass(frozen=True)
class RunJobResult:
    job_config: sqlite3.Row
    artifact: sqlite3.Row


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
    return RunJobResult(job_config=job_config_row, artifact=artifact_row)
