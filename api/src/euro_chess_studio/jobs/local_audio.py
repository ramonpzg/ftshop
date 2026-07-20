"""Local text-to-audio inference. Heavy dependencies load lazily so the
base install stays light; `just install-audio` pulls them in.

Models:
- facebook/musicgen-small via transformers, 32 kHz mono, token-based.
- stabilityai/stable-audio-open-1.0 via diffusers, 44.1 kHz stereo.
  Gated repo: accept the license on Hugging Face and set HF_TOKEN.

Pipelines cache at module level so the first generation pays the model
load and the rest do not.
"""

from typing import Any


class AudioDepsMissingError(RuntimeError):
    pass


class AudioGenerationError(RuntimeError):
    pass


_MUSICGEN_HINT = (
    "local audio dependencies are not installed. Run: just install-audio "
    "(pulls torch, transformers, diffusers, scipy, soundfile)"
)
_STABLE_AUDIO_HINT = (
    "stable-audio-open-1.0 is a gated repo: accept the license on "
    "huggingface.co/stabilityai/stable-audio-open-1.0 and set HF_TOKEN"
)

_musicgen_pipeline: Any = None
_stable_audio_pipeline: Any = None


def generate_musicgen(prompt: str, duration_seconds: float = 5.0) -> tuple[bytes, int]:
    """(wav bytes, sample rate) for a short music clip."""
    global _musicgen_pipeline
    try:
        import scipy.io.wavfile
        from transformers import pipeline
    except ImportError as exc:
        raise AudioDepsMissingError(_MUSICGEN_HINT) from exc

    if _musicgen_pipeline is None:
        _musicgen_pipeline = pipeline("text-to-audio", "facebook/musicgen-small")

    # MusicGen produces roughly 50 audio tokens per second.
    max_new_tokens = max(64, min(1500, int(duration_seconds * 50)))
    try:
        result = _musicgen_pipeline(
            prompt, forward_params={"do_sample": True, "max_new_tokens": max_new_tokens}
        )
    except Exception as exc:
        raise AudioGenerationError(f"musicgen generation failed: {exc}") from exc

    import io

    buffer = io.BytesIO()
    scipy.io.wavfile.write(buffer, rate=result["sampling_rate"], data=result["audio"])
    return buffer.getvalue(), int(result["sampling_rate"])


def generate_stable_audio(prompt: str, duration_seconds: float = 5.0) -> tuple[bytes, int]:
    """(wav bytes, sample rate) for a short sound effect."""
    global _stable_audio_pipeline
    try:
        import soundfile
        import torch
        from diffusers import StableAudioPipeline
    except ImportError as exc:
        raise AudioDepsMissingError(_MUSICGEN_HINT) from exc

    if _stable_audio_pipeline is None:
        try:
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            pipe = StableAudioPipeline.from_pretrained(
                "stabilityai/stable-audio-open-1.0", torch_dtype=dtype
            )
            if torch.cuda.is_available():
                pipe = pipe.to("cuda")
            _stable_audio_pipeline = pipe
        except Exception as exc:
            raise AudioGenerationError(f"{_STABLE_AUDIO_HINT}. Load failed: {exc}") from exc

    try:
        audio = _stable_audio_pipeline(
            prompt,
            negative_prompt="Low quality.",
            num_inference_steps=100,
            audio_end_in_s=min(10.0, max(1.0, duration_seconds)),
        ).audios
    except Exception as exc:
        raise AudioGenerationError(f"stable audio generation failed: {exc}") from exc

    import io

    sample_rate = int(_stable_audio_pipeline.vae.sampling_rate)
    buffer = io.BytesIO()
    soundfile.write(buffer, audio[0].T.float().cpu().numpy(), sample_rate, format="WAV")
    return buffer.getvalue(), sample_rate


def local_audio_available() -> bool:
    from importlib.util import find_spec

    return find_spec("transformers") is not None and find_spec("torch") is not None
