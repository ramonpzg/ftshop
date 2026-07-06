"""Runner for generation jobs that execute on fal.ai.

Outputs are downloaded into artifacts/generated and served from this
backend, so a result survives fal's URL lifetime and replays offline.
"""

import sqlite3

from euro_chess_studio.calculations.generation import (
    build_audio_fal_request,
    build_image_request,
    build_video_request,
    extract_output_url,
    file_extension_for,
)
from euro_chess_studio.calculations.ids import generate_id
from euro_chess_studio.config import get_generated_dir
from euro_chess_studio.data import fal_client
from euro_chess_studio.data.generated_store import save_generated
from euro_chess_studio.jobs.base import JobConfig, JobOutput


class GenerationError(RuntimeError):
    pass


_BUILDERS = {
    "image.generate": ("image", build_image_request),
    "video.generate": ("video", build_video_request),
    "audio.generate": ("audio", build_audio_fal_request),
}


class FalRunner:
    """Runs a generation job on fal's queue and stores the output locally."""

    def run(self, conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
        modality, builder = _BUILDERS[job.job_type]
        prompt = str(job.params.get("prompt", "")).strip()
        if not prompt:
            raise GenerationError("prompt must not be empty")
        model_key = str(job.params.get("model", ""))

        model_id, payload = builder(model_key, prompt)
        result = fal_client.run_model(model_id, payload)
        url = extract_output_url(result)
        if url is None:
            raise GenerationError(f"fal result had no output url: {str(result)[:200]}")

        content = fal_client.download_file(url)
        name = f"{generate_id('gen')}.{file_extension_for(url, modality)}"
        save_generated(get_generated_dir(), name, content)

        return JobOutput(
            modality=modality,
            kind=f"generated_{modality}",
            payload={
                "file_url": f"/artifacts/files/{name}",
                "remote_url": url,
                "prompt": prompt,
                "model": model_key,
                "model_id": model_id,
            },
        )
