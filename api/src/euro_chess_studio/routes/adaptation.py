"""Routes for the adaptation evidence chain: panel state and dataset
snapshot freezing. Training and benchmarking run through POST /jobs
like every other job; these routes only read state and freeze data."""

import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from euro_chess_studio.actions.adaptation import freeze_dataset_snapshot, get_adaptation_state
from euro_chess_studio.calculations.adaptation import AdaptationError
from euro_chess_studio.deps import get_db

router = APIRouter(tags=["adaptation"])


@router.get("/adaptation/state")
def get_state(conn: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    return get_adaptation_state(conn)


class FreezeSnapshotRequest(BaseModel):
    label: str | None = None


@router.post("/adaptation/snapshots", status_code=201)
def post_snapshot(
    body: FreezeSnapshotRequest, conn: sqlite3.Connection = Depends(get_db)
) -> dict[str, Any]:
    try:
        snapshot = freeze_dataset_snapshot(conn, label=body.label)
    except AdaptationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    data = dict(snapshot)
    data.pop("rows_json")
    data.pop("source_row_ids_json")
    return data
