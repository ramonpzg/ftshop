import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from euro_chess_studio.actions.errors import JobInProgressError, WorkspaceNotFoundError
from euro_chess_studio.actions.jobs import run_job
from euro_chess_studio.calculations.adaptation import AdaptationError
from euro_chess_studio.calculations.generation import (
    UnknownModelError,
    requests_presenter_generation,
)
from euro_chess_studio.data.adaptation_fixtures import AdaptationFixtureError
from euro_chess_studio.data.fal_client import FalNotConfiguredError, FalRequestError
from euro_chess_studio.data.llm_client import LlmNotConfiguredError
from euro_chess_studio.deps import get_db
from euro_chess_studio.jobs.fal_runner import GenerationError
from euro_chess_studio.jobs.local_audio import AudioDepsMissingError, AudioGenerationError
from euro_chess_studio.jobs.registry import UnknownJobTypeError, list_job_types
from euro_chess_studio.jobs.replay_runner import FixtureNotFoundError
from euro_chess_studio.routes.artifacts import ArtifactOut, artifact_out
from euro_chess_studio.routes.client_host import require_presenter_machine

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
def post_job(
    body: RunJobRequest, request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> RunJobResponse:
    # Generation is presenter-controlled: the full-room guardrail says
    # no attendee browser may spend the presenter's provider budget or
    # the presenter machine's compute. Free jobs (replays, local
    # calculations) stay open to the room.
    if requests_presenter_generation(body.job_type, body.params):
        require_presenter_machine(request, "generation")
    try:
        result = run_job(conn, body.job_type, body.params, body.workspace_id)
    except (UnknownJobTypeError, UnknownModelError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FixtureNotFoundError, AdaptationFixtureError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AdaptationError as exc:
        # The request names real objects but cannot be satisfied
        # honestly against current state (a cached replay asked to pose
        # as other data, a missing adapter, overlapping identities).
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except JobInProgressError as exc:
        # A duplicate single-flight run (live benchmark) was refused;
        # the in-flight run is the answer the caller should wait for.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (FalNotConfiguredError, AudioDepsMissingError, LlmNotConfiguredError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (FalRequestError, GenerationError, AudioGenerationError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return RunJobResponse(
        job_config=JobConfigOut(**dict(result.job_config)),
        artifact=artifact_out(result.artifact),
    )
