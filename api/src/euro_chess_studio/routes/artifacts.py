import json
import re
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from euro_chess_studio.config import get_artifacts_dir
from euro_chess_studio.data.artifacts_repo import list_artifacts, list_artifacts_for_workspace
from euro_chess_studio.deps import get_db

router = APIRouter(tags=["artifacts"])

_SAFE_MODALITY = re.compile(r"^[a-z]+$")
_SAFE_MEDIA_NAME = re.compile(r"^[a-z0-9_\-]+\.[a-z0-9]+$")


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


@router.get("/artifacts/media/{modality}/{name}")
def get_cached_media(modality: str, name: str) -> FileResponse:
    """Serves the committed workshop media under artifacts/cached/media.
    These are the local fallbacks that keep expired provider URLs and
    venue network failure from breaking a reveal; read-only, path
    segments strictly validated."""
    if not _SAFE_MODALITY.match(modality) or not _SAFE_MEDIA_NAME.match(name):
        raise HTTPException(status_code=404, detail="no such media file")
    path = get_artifacts_dir() / "cached" / "media" / modality / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="no such media file")
    return FileResponse(path)


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
