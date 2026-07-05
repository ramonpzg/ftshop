import json
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from euro_chess_studio.data.artifacts_repo import list_artifacts, list_artifacts_for_workspace
from euro_chess_studio.deps import get_db

router = APIRouter(tags=["artifacts"])


class ArtifactOut(BaseModel):
    id: str
    job_config_id: str | None
    modality: str
    kind: str
    payload: dict[str, Any]
    cached: bool
    created_at: str


def artifact_out(row: sqlite3.Row) -> ArtifactOut:
    data = dict(row)
    data["payload"] = json.loads(data.pop("payload_json"))
    return ArtifactOut(**data)


@router.get("/artifacts")
def get_artifacts(
    modality: str | None = None,
    workspace_id: str | None = None,
    conn: sqlite3.Connection = Depends(get_db),
) -> list[ArtifactOut]:
    if workspace_id is not None:
        rows = list_artifacts_for_workspace(conn, workspace_id)
        if modality is not None:
            rows = [row for row in rows if row["modality"] == modality]
    else:
        rows = list_artifacts(conn, modality)
    return [artifact_out(row) for row in rows]
