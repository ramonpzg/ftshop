"""Runner for audio.generate: local models when the audio extra is
installed, fal as the remote fallback. The dispatch by model key lives
here so the UI keeps saying only "run audio.generate"."""

import sqlite3

from euro_chess_studio.calculations.generation import AUDIO_MODELS, UnknownModelError
from euro_chess_studio.calculations.ids import generate_id
from euro_chess_studio.config import get_generated_dir
from euro_chess_studio.data.generated_store import save_generated
from euro_chess_studio.jobs import local_audio
from euro_chess_studio.jobs.base import JobConfig, JobOutput
from euro_chess_studio.jobs.fal_runner import FalRunner, GenerationError

_LOCAL_GENERATORS = {
    "local-musicgen": local_audio.generate_musicgen,
    "local-stable-audio": local_audio.generate_stable_audio,
}


class AudioRunner:
    def run(self, conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
        model_key = str(job.params.get("model", ""))
        model = AUDIO_MODELS.get(model_key)
        if model is None:
            raise UnknownModelError(f"unknown audio model: {model_key}")

        if model["engine"] == "fal":
            return FalRunner().run(conn, job)

        prompt = str(job.params.get("prompt", "")).strip()
        if not prompt:
            raise GenerationError("prompt must not be empty")
        duration = float(job.params.get("duration_seconds", 5.0))

        generate = _LOCAL_GENERATORS[model["engine"]]
        wav_bytes, sample_rate = generate(prompt, duration)

        name = f"{generate_id('gen')}.wav"
        save_generated(get_generated_dir(), name, wav_bytes)

        return JobOutput(
            modality="audio",
            kind="generated_audio",
            payload={
                "file_url": f"/artifacts/files/{name}",
                "prompt": prompt,
                "model": model_key,
                "sample_rate": sample_rate,
                "duration_seconds": duration,
            },
        )
