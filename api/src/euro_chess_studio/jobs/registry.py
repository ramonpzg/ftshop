"""Maps job types to the runner that handles them. This is the only place
that decision is made -- the UI and the API just say "run job_type X".
"""

from euro_chess_studio.jobs.audio_runner import AudioRunner
from euro_chess_studio.jobs.base import JobRunner
from euro_chess_studio.jobs.cloud_runner import CloudRunner
from euro_chess_studio.jobs.fal_runner import FalRunner
from euro_chess_studio.jobs.local_runner import LocalRunner
from euro_chess_studio.jobs.replay_runner import ReplayRunner

RUNNER_NAME_BY_JOB_TYPE: dict[str, str] = {
    "text.prompt_eval": "local",
    "text.reward_eval": "local",
    "image.show_dataset": "replay",
    "image.generate": "fal",
    "audio.make_spectrogram": "local",
    "audio.generate": "audio",
    "video.sample_frames": "local",
    "video.generate": "fal",
    "artifact.reveal_cached": "replay",
}

_RUNNERS_BY_NAME: dict[str, JobRunner] = {
    "local": LocalRunner(),
    "replay": ReplayRunner(),
    "cloud": CloudRunner(),
    "fal": FalRunner(),
    "audio": AudioRunner(),
}


class UnknownJobTypeError(ValueError):
    pass


def list_job_types() -> list[str]:
    return sorted(RUNNER_NAME_BY_JOB_TYPE)


def get_runner_for_job_type(job_type: str) -> JobRunner:
    runner_name = RUNNER_NAME_BY_JOB_TYPE.get(job_type)
    if runner_name is None:
        raise UnknownJobTypeError(f"unknown job type: {job_type}")
    return _RUNNERS_BY_NAME[runner_name]
