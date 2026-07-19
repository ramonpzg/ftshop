import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from euro_chess_studio.data.eval_results_repo import list_eval_results
from euro_chess_studio.deps import get_db

router = APIRouter(tags=["evals"])


class EvalResultOut(BaseModel):
    id: str
    modality: str
    metric: str
    value: float
    workspace_id: str | None
    source: str
    # Provenance: computed rows carry sample counts and the metric
    # definition; cached rows carry the fixture's note.
    numerator: int | None = None
    denominator: int | None = None
    unit: str | None = None
    direction: str | None = None
    definition: str | None = None
    version: str | None = None
    scope_json: str | None = None
    note: str | None = None
    created_at: str


@router.get("/evals")
def get_evals(
    modality: str | None = None,
    workspace_id: str | None = None,
    conn: sqlite3.Connection = Depends(get_db),
) -> list[EvalResultOut]:
    rows = list_eval_results(conn, modality=modality, workspace_id=workspace_id)
    return [EvalResultOut(**dict(row)) for row in rows]
