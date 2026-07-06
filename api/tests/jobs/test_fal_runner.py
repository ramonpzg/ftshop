from pathlib import Path

import pytest

from euro_chess_studio.calculations.generation import UnknownModelError
from euro_chess_studio.jobs import fal_runner
from euro_chess_studio.jobs.base import JobConfig
from euro_chess_studio.jobs.fal_runner import FalRunner, GenerationError


@pytest.fixture
def generated_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "generated"
    monkeypatch.setenv("CHESS_STUDIO_GENERATED_DIR", str(target))
    return target


def fake_fal(monkeypatch: pytest.MonkeyPatch, response: dict, content: bytes = b"bytes"):
    calls: dict = {}

    def run_model(model_id, payload, **kwargs):
        calls["model_id"] = model_id
        calls["payload"] = payload
        return response

    monkeypatch.setattr(fal_runner.fal_client, "run_model", run_model)
    monkeypatch.setattr(fal_runner.fal_client, "download_file", lambda url, **k: content)
    return calls


def test_image_generate_downloads_and_serves_locally(
    generated_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    calls = fake_fal(monkeypatch, {"images": [{"url": "https://fal.media/x/out.png"}]}, b"\x89PNG")
    output = FalRunner().run(
        None,
        JobConfig(
            job_type="image.generate", params={"prompt": "a knight", "model": "flux-2-klein"}
        ),
    )

    assert calls["model_id"] == "fal-ai/flux-2/klein/4b"
    assert output.modality == "image"
    assert output.kind == "generated_image"
    name = output.payload["file_url"].rsplit("/", 1)[-1]
    assert (generated_dir / name).read_bytes() == b"\x89PNG"
    assert output.payload["remote_url"] == "https://fal.media/x/out.png"


def test_video_generate_uses_video_slot(generated_dir: Path, monkeypatch: pytest.MonkeyPatch):
    fake_fal(monkeypatch, {"video": {"url": "https://fal.media/x/clip.mp4"}})
    output = FalRunner().run(
        None, JobConfig(job_type="video.generate", params={"prompt": "a fork", "model": "ltx-fast"})
    )
    assert output.modality == "video"
    assert output.payload["file_url"].endswith(".mp4")


def test_empty_prompt_is_rejected_before_any_network_call(
    generated_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    def explode(*args, **kwargs):
        raise AssertionError("must not reach fal")

    monkeypatch.setattr(fal_runner.fal_client, "run_model", explode)
    with pytest.raises(GenerationError):
        FalRunner().run(
            None,
            JobConfig(job_type="image.generate", params={"prompt": " ", "model": "flux-2-klein"}),
        )


def test_unknown_model_is_rejected(generated_dir: Path, monkeypatch: pytest.MonkeyPatch):
    fake_fal(monkeypatch, {})
    with pytest.raises(UnknownModelError):
        FalRunner().run(
            None,
            JobConfig(job_type="image.generate", params={"prompt": "x", "model": "evil/model"}),
        )


def test_missing_output_url_raises(generated_dir: Path, monkeypatch: pytest.MonkeyPatch):
    fake_fal(monkeypatch, {"status": "COMPLETED"})
    with pytest.raises(GenerationError):
        FalRunner().run(
            None,
            JobConfig(job_type="image.generate", params={"prompt": "x", "model": "flux-2-klein"}),
        )
