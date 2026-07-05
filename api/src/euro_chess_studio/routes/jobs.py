import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from euro_chess_studio.actions.jobs import run_job
from euro_chess_studio.deps import get_db
from euro_chess_studio.jobs.registry import UnknownJobTypeError, list_job_types
from euro_chess_studio.jobs.replay_runner import FixtureNotFoundError
from euro_chess_studio.routes.artifacts import ArtifactOut, artifact_out

router = APIRouter(tags=["jobs"])


@router.get("/jobs/types")
def get_job_types() -> list[str]:
    return list_job_types()


class RunJobRequest(BaseModel):
    job_type: str
    params: dict[str, Any] = {}
    workspace_id: str | None = None


class JobConfigOut(BaseModel):
    id: str
    workspace_id: str | None
    job_type: str
    params_json: str
    created_at: str


class RunJobResponse(BaseModel):
    job_config: JobConfigOut
    artifact: ArtifactOut


@router.post("/jobs")
def post_job(body: RunJobRequest, conn: sqlite3.Connection = Depends(get_db)) -> RunJobResponse:
    try:
        result = run_job(conn, body.job_type, body.params, body.workspace_id)
    except UnknownJobTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FixtureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RunJobResponse(
        job_config=JobConfigOut(**dict(result.job_config)),
        artifact=artifact_out(result.artifact),
    )
