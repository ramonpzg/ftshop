"""Action: run a job. Persists the job config and the resulting artifact."""

import sqlite3
from dataclasses import dataclass

from euro_chess_studio.data.artifacts_repo import insert_artifact
from euro_chess_studio.data.job_configs_repo import insert_job_config
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

    # Run first, persist after: a failed generation (missing API key,
    # provider error) must not leave an orphaned config row behind.
    output = runner.run(
        conn, JobConfig(job_type=job_type, params=params, workspace_id=workspace_id)
    )
    job_config_row = insert_job_config(
        conn, workspace_id=workspace_id, job_type=job_type, params=params
    )
    artifact_row = insert_artifact(
        conn,
        job_config_id=job_config_row["id"],
        modality=output.modality,
        kind=output.kind,
        payload=output.payload,
        cached=output.cached,
    )
    # Handlers may have written eval_results; those repos no longer
    # commit, so the job's whole result persists here or not at all.
    conn.commit()
    return RunJobResult(job_config=job_config_row, artifact=artifact_row)
