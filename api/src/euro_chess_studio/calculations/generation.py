"""Pure model catalogs and request builders for generation jobs.

The catalogs are allowlists: the frontend sends a short model key, never
a raw provider model id, so a client cannot point the backend at an
arbitrary endpoint.
"""

IMAGE_MODELS: dict[str, dict] = {
    "flux-2-klein": {"label": "FLUX.2 Klein 4B", "fal_id": "fal-ai/flux-2/klein/4b"},
    "flux-schnell": {"label": "FLUX.1 schnell", "fal_id": "fal-ai/flux/schnell"},
}

VIDEO_MODELS: dict[str, dict] = {
    "ltx-fast": {"label": "LTX 2.3 fast", "fal_id": "fal-ai/ltx-2.3/text-to-video/fast"},
    "veo-fast": {"label": "Veo 3.1 fast", "fal_id": "fal-ai/veo3.1/fast"},
}

AUDIO_MODELS: dict[str, dict] = {
    "musicgen-small": {"label": "MusicGen small, local", "engine": "local-musicgen"},
    "stable-audio-open": {"label": "Stable Audio Open, local", "engine": "local-stable-audio"},
    "ace-step": {"label": "ACE-Step, fal", "engine": "fal", "fal_id": "fal-ai/ace-step"},
}


class UnknownModelError(ValueError):
    pass


def build_image_request(model_key: str, prompt: str) -> tuple[str, dict]:
    model = IMAGE_MODELS.get(model_key)
    if model is None:
        raise UnknownModelError(f"unknown image model: {model_key}")
    return model["fal_id"], {
        "prompt": prompt,
        "image_size": "square_hd",
        "num_images": 1,
        "output_format": "png",
    }


def build_video_request(model_key: str, prompt: str) -> tuple[str, dict]:
    model = VIDEO_MODELS.get(model_key)
    if model is None:
        raise UnknownModelError(f"unknown video model: {model_key}")
    if model_key == "veo-fast":
        # Veo takes duration as a string with an s suffix, unlike LTX.
        return model["fal_id"], {"prompt": prompt, "duration": "6s", "resolution": "720p"}
    return model["fal_id"], {
        "prompt": prompt,
        "duration": 6,
        "resolution": "1080p",
        "fps": 25,
    }


def build_audio_fal_request(model_key: str, prompt: str) -> tuple[str, dict]:
    model = AUDIO_MODELS.get(model_key)
    if model is None or model.get("engine") != "fal":
        raise UnknownModelError(f"unknown fal audio model: {model_key}")
    return model["fal_id"], {"prompt": prompt, "duration": 15}


def extract_output_url(response: dict) -> str | None:
    """The output file URL from a fal result, wherever this model family
    put it. Checked in a fixed order so behavior is deterministic."""
    images = response.get("images")
    if isinstance(images, list) and images and isinstance(images[0], dict):
        url = images[0].get("url")
        if isinstance(url, str):
            return url
    for key in ("video", "audio", "audio_file"):
        slot = response.get(key)
        if isinstance(slot, dict) and isinstance(slot.get("url"), str):
            return slot["url"]
    url = response.get("audio_url")
    if isinstance(url, str):
        return url
    return None


def file_extension_for(url: str, kind: str) -> str:
    """Extension for the downloaded output, from the URL when it has one
    and from the modality when it does not."""
    path = url.split("?")[0]
    if "." in path.rsplit("/", 1)[-1]:
        ext = path.rsplit(".", 1)[-1].lower()
        if ext.isalnum() and len(ext) <= 5:
            return ext
    return {"image": "png", "video": "mp4", "audio": "wav"}.get(kind, "bin")
