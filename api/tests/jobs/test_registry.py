import pytest

from euro_chess_studio.jobs.cloud_runner import CloudRunner
from euro_chess_studio.jobs.local_runner import LocalRunner
from euro_chess_studio.jobs.registry import (
    UnknownJobTypeError,
    get_runner_for_job_type,
    list_job_types,
)
from euro_chess_studio.jobs.replay_runner import ReplayRunner


def test_list_job_types_includes_all_job_types():
    types = list_job_types()
    assert set(types) == {
        "text.prompt_eval",
        "text.reward_eval",
        "text.train_adapter",
        "text.benchmark_eval",
        "image.show_dataset",
        "image.generate",
        "image.adaptation_evidence",
        "audio.make_spectrogram",
        "audio.generate",
        "audio.adaptation_evidence",
        "video.sample_frames",
        "video.generate",
        "video.adaptation_evidence",
        "artifact.reveal_cached",
    }


def test_local_job_types_resolve_to_local_runner():
    assert isinstance(get_runner_for_job_type("text.prompt_eval"), LocalRunner)
    assert isinstance(get_runner_for_job_type("audio.make_spectrogram"), LocalRunner)


def test_replay_job_types_resolve_to_replay_runner():
    assert isinstance(get_runner_for_job_type("image.show_dataset"), ReplayRunner)
    assert isinstance(get_runner_for_job_type("artifact.reveal_cached"), ReplayRunner)


def test_unknown_job_type_raises():
    with pytest.raises(UnknownJobTypeError):
        get_runner_for_job_type("not.a.job")


def test_cloud_runner_is_a_documented_stub(tmp_path):
    runner = CloudRunner()
    with pytest.raises(NotImplementedError):
        runner.run(None, None)  # type: ignore[arg-type]
