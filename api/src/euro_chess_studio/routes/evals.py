import json
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
    # model/checkpoint identify which version this result scopes to, so
    # a base and an adapted model's rows can be told apart at a glance.
    # run_id groups every metric one job execution produced. sample_ids
    # is an audit trail back to the exact move/attempt rows counted.
    model: str | None = None
    checkpoint: str | None = None
    run_id: str | None = None
    sample_ids: list[str] = []
    # The actual frozen input set: the exact fens the sample rows were
    # about, and a deterministic hash of that set. Two rows with
    # matching position_set_id were measured over the identical
    # positions and are honestly comparable; different ids mean they
    # were not, regardless of how similar model/checkpoint look.
    position_set_id: str | None = None
    positions: list[str] = []
    created_at: str


def _eval_result_out(row: sqlite3.Row) -> EvalResultOut:
    data = dict(row)
    sample_ids_json = data.pop("sample_ids_json", None)
    data["sample_ids"] = json.loads(sample_ids_json) if sample_ids_json else []
    position_set_json = data.pop("position_set_json", None)
    data["positions"] = json.loads(position_set_json) if position_set_json else []
    return EvalResultOut(**data)


@router.get("/evals")
def get_evals(
    modality: str | None = None,
    workspace_id: str | None = None,
    conn: sqlite3.Connection = Depends(get_db),
) -> list[EvalResultOut]:
    rows = list_eval_results(conn, modality=modality, workspace_id=workspace_id)
    return [_eval_result_out(row) for row in rows]
