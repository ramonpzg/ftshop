from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from euro_chess_studio.config import get_assets_dir, get_canvas_dir
from euro_chess_studio.data import assets_store, canvas_store

router = APIRouter(tags=["canvas"])


class CanvasSnapshotIn(BaseModel):
    snapshot: dict[str, Any]


class CanvasSnapshotOut(BaseModel):
    snapshot: dict[str, Any] | None


@router.get("/canvas")
def get_canvas() -> CanvasSnapshotOut:
    return CanvasSnapshotOut(snapshot=canvas_store.read_snapshot(get_canvas_dir()))


@router.put("/canvas")
def put_canvas(body: CanvasSnapshotIn) -> dict[str, bool]:
    canvas_store.write_snapshot(get_canvas_dir(), body.snapshot)
    return {"saved": True}


@router.post("/canvas/assets")
async def upload_asset(file: UploadFile) -> dict[str, str]:
    name = file.filename or ""
    if not assets_store.is_safe_name(name):
        raise HTTPException(status_code=400, detail=f"unsafe asset name: {name!r}")
    content = await file.read()
    assets_store.save_asset(get_assets_dir(), name, content)
    return {"name": name}


@router.get("/canvas/assets")
def list_assets() -> dict[str, list[str]]:
    return {"names": assets_store.list_asset_names(get_assets_dir())}


@router.get("/canvas/assets/{name}")
def get_asset(name: str) -> FileResponse:
    path = assets_store.asset_path(get_assets_dir(), name)
    if path is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return FileResponse(path)


@router.delete("/canvas/assets/{name}")
def delete_asset(name: str) -> dict[str, bool]:
    return {"deleted": assets_store.delete_asset(get_assets_dir(), name)}
