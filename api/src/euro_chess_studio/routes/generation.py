from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from euro_chess_studio.calculations.generation import AUDIO_MODELS, IMAGE_MODELS, VIDEO_MODELS
from euro_chess_studio.config import get_generated_dir
from euro_chess_studio.data.fal_client import is_fal_configured
from euro_chess_studio.data.generated_store import generated_path
from euro_chess_studio.jobs.local_audio import local_audio_available

router = APIRouter(tags=["generation"])


class ModelOption(BaseModel):
    id: str
    label: str
    available: bool


class ModalityOptions(BaseModel):
    configured: bool
    models: list[ModelOption]


class GenerationOptionsOut(BaseModel):
    image: ModalityOptions
    video: ModalityOptions
    audio: ModalityOptions


@router.get("/generation/options")
def get_generation_options() -> GenerationOptionsOut:
    fal = is_fal_configured()
    local = local_audio_available()

    def fal_models(catalog: dict) -> list[ModelOption]:
        return [
            ModelOption(id=key, label=model["label"], available=fal)
            for key, model in catalog.items()
        ]

    audio_models = [
        ModelOption(
            id=key,
            label=model["label"],
            available=fal if model["engine"] == "fal" else local,
        )
        for key, model in AUDIO_MODELS.items()
    ]
    return GenerationOptionsOut(
        image=ModalityOptions(configured=fal, models=fal_models(IMAGE_MODELS)),
        video=ModalityOptions(configured=fal, models=fal_models(VIDEO_MODELS)),
        audio=ModalityOptions(
            configured=local or fal,
            models=audio_models,
        ),
    )


@router.get("/artifacts/files/{name}")
def get_generated_file(name: str) -> FileResponse:
    path = generated_path(get_generated_dir(), name)
    if path is None:
        raise HTTPException(status_code=404, detail="no generated file with that name")
    return FileResponse(path)
