from pathlib import Path

import pytest

from euro_chess_studio.calculations.generation import UnknownModelError
from euro_chess_studio.jobs import audio_runner
from euro_chess_studio.jobs.audio_runner import AudioRunner
from euro_chess_studio.jobs.base import JobConfig
from euro_chess_studio.jobs.local_audio import AudioDepsMissingError


@pytest.fixture
def generated_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "generated"
    monkeypatch.setenv("CHESS_STUDIO_GENERATED_DIR", str(target))
    return target


def test_local_model_writes_wav_and_reports_metadata(
    generated_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setitem(
        audio_runner._LOCAL_GENERATORS,
        "local-musicgen",
        lambda prompt, duration: (b"RIFFwav", 32000),
    )
    output = AudioRunner().run(
        None,
        JobConfig(
            job_type="audio.generate",
            params={"prompt": "wood capture click", "model": "musicgen-small"},
        ),
    )
    assert output.kind == "generated_audio"
    assert output.payload["sample_rate"] == 32000
    name = output.payload["file_url"].rsplit("/", 1)[-1]
    assert (generated_dir / name).read_bytes() == b"RIFFwav"


def test_missing_local_deps_surface_the_install_hint(
    generated_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    def raise_missing(prompt, duration):
        raise AudioDepsMissingError("run: just install-audio")

    monkeypatch.setitem(audio_runner._LOCAL_GENERATORS, "local-musicgen", raise_missing)
    with pytest.raises(AudioDepsMissingError):
        AudioRunner().run(
            None,
            JobConfig(job_type="audio.generate", params={"prompt": "x", "model": "musicgen-small"}),
        )


def test_fal_engine_models_delegate_to_the_fal_runner(
    generated_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    from euro_chess_studio.jobs import fal_runner

    monkeypatch.setattr(
        fal_runner.fal_client, "run_model", lambda *a, **k: {"audio": {"url": "https://x/a.wav"}}
    )
    monkeypatch.setattr(fal_runner.fal_client, "download_file", lambda url, **k: b"RIFF")
    output = AudioRunner().run(
        None,
        JobConfig(job_type="audio.generate", params={"prompt": "a beat", "model": "ace-step"}),
    )
    assert output.modality == "audio"
    assert output.payload["model"] == "ace-step"


def test_unknown_audio_model_is_rejected(generated_dir: Path):
    with pytest.raises(UnknownModelError):
        AudioRunner().run(
            None, JobConfig(job_type="audio.generate", params={"prompt": "x", "model": "nope"})
        )
