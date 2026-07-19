import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from euro_chess_studio.actions.export import (
    EXPORT_FILE_NAME,
    FULL_EXPORT_FILE_NAME,
    SCENARIO_EXPORT_FILE_NAME,
    export_full_dataset,
    export_scenarios,
    export_text_dataset,
    get_full_export_path,
    get_scenario_export_path,
    get_text_export_path,
)
from euro_chess_studio.deps import get_db

router = APIRouter(tags=["datasets"])


class ExportOut(BaseModel):
    file_name: str
    row_count: int
    url: str


@router.post("/datasets/text/export")
def post_export(conn: sqlite3.Connection = Depends(get_db)) -> ExportOut:
    result = export_text_dataset(conn)
    return ExportOut(
        file_name=result.file_name,
        row_count=result.row_count,
        url=f"/datasets/text/{result.file_name}",
    )


@router.get(f"/datasets/text/{EXPORT_FILE_NAME}")
def get_export_file() -> FileResponse:
    path = get_text_export_path()
    if not path.is_file():
        raise HTTPException(
            status_code=404, detail="no export yet. POST /datasets/text/export first"
        )
    return FileResponse(path, media_type="application/jsonl", filename=EXPORT_FILE_NAME)


@router.post("/datasets/text/export-full")
def post_export_full(conn: sqlite3.Connection = Depends(get_db)) -> ExportOut:
    result = export_full_dataset(conn)
    return ExportOut(
        file_name=result.file_name,
        row_count=result.row_count,
        url=f"/datasets/text/{result.file_name}",
    )


@router.get(f"/datasets/text/{FULL_EXPORT_FILE_NAME}")
def get_full_export_file() -> FileResponse:
    path = get_full_export_path()
    if not path.is_file():
        raise HTTPException(
            status_code=404, detail="no export yet. POST /datasets/text/export-full first"
        )
    return FileResponse(path, media_type="application/jsonl", filename=FULL_EXPORT_FILE_NAME)


@router.post("/datasets/scenarios/export")
def post_export_scenarios(conn: sqlite3.Connection = Depends(get_db)) -> ExportOut:
    result = export_scenarios(conn)
    return ExportOut(
        file_name=result.file_name,
        row_count=result.row_count,
        url=f"/datasets/text/{result.file_name}",
    )


@router.get(f"/datasets/text/{SCENARIO_EXPORT_FILE_NAME}")
def get_scenario_export_file() -> FileResponse:
    path = get_scenario_export_path()
    if not path.is_file():
        raise HTTPException(
            status_code=404, detail="no export yet. POST /datasets/scenarios/export first"
        )
    return FileResponse(path, media_type="application/jsonl", filename=SCENARIO_EXPORT_FILE_NAME)
