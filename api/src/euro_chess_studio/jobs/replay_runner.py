import json
import re
import sqlite3

from euro_chess_studio.config import get_artifacts_dir
from euro_chess_studio.jobs.base import JobConfig, JobOutput

_SAFE_SEGMENT = re.compile(r"^[a-z0-9_\-]+$")


class FixtureNotFoundError(ValueError):
    pass


def _fixture_path(job: JobConfig) -> str:
    if job.job_type == "image.show_dataset":
        return "image/show_dataset.json"
    if job.job_type == "artifact.reveal_cached":
        modality = job.params.get("modality")
        key = job.params.get("key")
        if not modality or not key:
            raise FixtureNotFoundError("artifact.reveal_cached requires 'modality' and 'key'")
        # Client-provided segments must never escape artifacts/cached.
        if not _SAFE_SEGMENT.match(str(modality)) or not _SAFE_SEGMENT.match(str(key)):
            raise FixtureNotFoundError(f"invalid fixture segments: {modality!r}/{key!r}")
        return f"{modality}/{key}.json"
    raise FixtureNotFoundError(f"no fixture mapping for job type: {job.job_type}")


class ReplayRunner:
    """Loads a deterministic cached artifact fixture from disk."""

    def run(self, conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
        relative_path = _fixture_path(job)
        path = get_artifacts_dir() / "cached" / relative_path
        if not path.exists():
            raise FixtureNotFoundError(f"no cached fixture at {path}")
        data = json.loads(path.read_text())
        return JobOutput(
            modality=data["modality"], kind=data["kind"], payload=data["payload"], cached=True
        )
