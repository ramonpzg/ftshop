import pytest

from euro_chess_studio.calculations.generation import (
    AUDIO_MODELS,
    IMAGE_MODELS,
    VIDEO_MODELS,
    UnknownModelError,
    build_audio_fal_request,
    build_image_request,
    build_video_request,
    extract_output_url,
    file_extension_for,
)


def test_image_request_uses_allowlisted_fal_id():
    model_id, payload = build_image_request("flux-2-klein", "a knight")
    assert model_id == "fal-ai/flux-2/klein/4b"
    assert payload["prompt"] == "a knight"
    assert payload["num_images"] == 1


def test_video_request_veo_uses_string_duration():
    _, ltx = build_video_request("ltx-fast", "a chess clip")
    _, veo = build_video_request("veo-fast", "a chess clip")
    assert isinstance(ltx["duration"], int)
    assert veo["duration"] == "6s"


def test_unknown_models_are_rejected():
    with pytest.raises(UnknownModelError):
        build_image_request("fal-ai/anything-i-want", "prompt")
    with pytest.raises(UnknownModelError):
        build_video_request("nope", "prompt")
    with pytest.raises(UnknownModelError):
        build_audio_fal_request("musicgen-small", "prompt")  # local model, not fal


def test_catalogs_have_labels():
    for catalog in (IMAGE_MODELS, VIDEO_MODELS, AUDIO_MODELS):
        for model in catalog.values():
            assert model["label"]


def test_extract_output_url_by_modality_shape():
    assert extract_output_url({"images": [{"url": "https://x/img.png"}]}) == "https://x/img.png"
    assert extract_output_url({"video": {"url": "https://x/v.mp4"}}) == "https://x/v.mp4"
    assert extract_output_url({"audio": {"url": "https://x/a.wav"}}) == "https://x/a.wav"
    assert extract_output_url({"audio_url": "https://x/a.mp3"}) == "https://x/a.mp3"
    assert extract_output_url({"something": "else"}) is None


def test_file_extension_prefers_url_then_modality():
    assert file_extension_for("https://x/files/out.png?sig=1", "image") == "png"
    assert file_extension_for("https://x/files/no-extension", "video") == "mp4"
    assert file_extension_for("https://x/files/no-extension", "audio") == "wav"
