"""Pure training configuration and hardware preflight calculations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

TrainingMethod = Literal["lora", "qlora"]

BASE_MODEL = "google/gemma-4-E2B-it-qat-q4_0-unquantized"
BASE_MODEL_REVISION = "6befbaca7398925921802abd1f277b495b78b738"
DEFAULT_REPO_PREFIX = "ramonpzg/gemma-4-e2b-chessking"
MIN_QLORA_VRAM_GIB = 7.5
MIN_LORA_VRAM_GIB = 16.0
MIN_QLORA_FREE_VRAM_GIB = 6.5
MIN_LORA_FREE_VRAM_GIB = 15.0


@dataclass(frozen=True)
class TrainerConfig:
    method: TrainingMethod
    max_seq_length: int = 1_024
    rank: int = 8
    alpha: int = 8
    dropout: float = 0.0
    learning_rate: float = 2e-4
    batch_size: int = 1
    gradient_accumulation_steps: int = 8
    max_steps: int = 60
    seed: int = 2026
    eval_samples: int = 8

    def as_dict(self) -> dict:
        return asdict(self)

    def validate(self) -> None:
        if self.max_seq_length < 128:
            raise ValueError("max_seq_length must be at least 128")
        if self.rank < 1 or self.alpha < 1:
            raise ValueError("rank and alpha must be positive")
        if self.max_steps < 1:
            raise ValueError("max_steps must be positive")
        if self.batch_size != 1:
            raise ValueError("this 8 GB recipe fixes batch_size at 1")
        if self.gradient_accumulation_steps < 1:
            raise ValueError("gradient_accumulation_steps must be positive")
        if self.eval_samples < 0:
            raise ValueError("eval_samples cannot be negative")


def check_vram(
    method: TrainingMethod,
    total_gib: float,
    *,
    free_gib: float | None = None,
    force: bool = False,
) -> None:
    required = MIN_QLORA_VRAM_GIB if method == "qlora" else MIN_LORA_VRAM_GIB
    minimum_free = MIN_QLORA_FREE_VRAM_GIB if method == "qlora" else MIN_LORA_FREE_VRAM_GIB
    if not force and total_gib < required and method == "lora":
        raise RuntimeError(
            f"LoRA needs at least {required:g} GiB in this recipe; found {total_gib:.1f} GiB. "
            "The base checkpoint alone is about 10.2 GB. Use --qlora here or run --lora "
            "on a larger GPU. --force-vram bypasses only this guard, not physics."
        )
    if not force and total_gib < required:
        raise RuntimeError(
            f"QLoRA needs at least {required:g} GiB; found {total_gib:.1f} GiB. Use a larger GPU."
        )
    if not force and free_gib is not None and free_gib < minimum_free:
        raise RuntimeError(
            f"{method.upper()} needs about {minimum_free:g} GiB free before loading; "
            f"found {free_gib:.1f} GiB free. Stop llama.cpp and other GPU jobs, then retry."
        )


def repository_for(prefix: str, method: TrainingMethod) -> str:
    return prefix if method == "qlora" else f"{prefix}-lora"


def model_load_options(config: TrainerConfig) -> dict[str, object]:
    return {
        "model_name": BASE_MODEL,
        "revision": BASE_MODEL_REVISION,
        "max_seq_length": config.max_seq_length,
        "load_in_4bit": config.method == "qlora",
        "load_in_16bit": config.method == "lora",
        "full_finetuning": False,
        "use_gradient_checkpointing": "unsloth",
        "text_only": True,
    }


def model_architectures(current: object, model_class_name: str) -> object:
    return current or [model_class_name]
