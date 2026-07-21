"""Unsloth training, adapter validation, and Hugging Face publishing."""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

from euro_chess_studio.calculations.llm_prompts import parse_move_reply
from huggingface_hub import HfApi

from chess_adapt.calculations.training import (
    BASE_MODEL,
    BASE_MODEL_REVISION,
    TrainerConfig,
    TrainingMethod,
    check_vram,
    repository_for,
)
from chess_adapt.data.store import PipelinePaths, read_json, read_jsonl, write_json


def preflight_training(method: TrainingMethod, *, force_vram: bool = False) -> dict[str, Any]:
    torch = importlib.import_module("torch")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the Unsloth training run")
    total_gib = torch.cuda.get_device_properties(0).total_memory / 1024**3
    free_gib = torch.cuda.mem_get_info()[0] / 1024**3
    check_vram(method, total_gib, free_gib=free_gib, force=force_vram)
    return {
        "name": torch.cuda.get_device_properties(0).name,
        "total_gib": total_gib,
        "free_gib": free_gib,
    }


def train_adapter(
    paths: PipelinePaths,
    config: TrainerConfig,
    *,
    overwrite: bool = False,
    force_vram: bool = False,
) -> dict[str, Any]:
    """Train and save one PEFT adapter. GPU imports stay inside this boundary."""
    config.validate()
    gpu = preflight_training(config.method, force_vram=force_vram)
    torch = importlib.import_module("torch")

    adapter_dir = paths.adapter(config.method)
    work_dir = paths.work(config.method)
    if adapter_dir.exists() and not overwrite:
        raise RuntimeError(
            f"adapter already exists at {adapter_dir}; pass --overwrite to replace it"
        )
    if overwrite:
        shutil.rmtree(adapter_dir.parent, ignore_errors=True)
    adapter_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    train_file = paths.split("train")
    if not read_jsonl(train_file):
        raise RuntimeError(f"no training rows at {train_file}; run --prepare first")

    datasets = importlib.import_module("datasets")
    unsloth = importlib.import_module("unsloth")
    templates = importlib.import_module("unsloth.chat_templates")
    trl = importlib.import_module("trl")
    FastModel = unsloth.FastModel

    model, tokenizer = FastModel.from_pretrained(
        model_name=BASE_MODEL,
        revision=BASE_MODEL_REVISION,
        max_seq_length=config.max_seq_length,
        load_in_4bit=config.method == "qlora",
        load_in_16bit=config.method == "lora",
        full_finetuning=False,
        use_gradient_checkpointing="unsloth",
    )
    model = FastModel.get_peft_model(
        model,
        finetune_vision_layers=False,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        r=config.rank,
        lora_alpha=config.alpha,
        lora_dropout=config.dropout,
        bias="none",
        random_state=config.seed,
    )
    tokenizer = templates.get_chat_template(tokenizer, chat_template="gemma-4")

    dataset: Any = datasets.load_dataset(
        "json", data_files={"train": str(train_file)}, split="train"
    )

    def format_messages(examples: dict[str, list]) -> dict[str, list[str]]:
        texts = [
            tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            ).removeprefix("<bos>")
            for messages in examples["messages"]
        ]
        return {"text": texts}

    dataset = dataset.map(format_messages, batched=True)
    trainer = trl.SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        eval_dataset=None,
        args=trl.SFTConfig(
            dataset_text_field="text",
            max_length=config.max_seq_length,
            per_device_train_batch_size=config.batch_size,
            gradient_accumulation_steps=config.gradient_accumulation_steps,
            warmup_steps=min(5, max(1, config.max_steps // 10)),
            max_steps=config.max_steps,
            learning_rate=config.learning_rate,
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.001,
            lr_scheduler_type="linear",
            seed=config.seed,
            dataset_num_proc=1,
            output_dir=str(work_dir),
            report_to="none",
            save_strategy="steps",
            save_steps=max(10, config.max_steps // 3),
            save_total_limit=1,
        ),
    )
    trainer = templates.train_on_responses_only(trainer)
    training_result = trainer.train()
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)

    validation = _validate_adapter(
        model,
        tokenizer,
        FastModel,
        torch,
        paths,
        limit=config.eval_samples,
    )
    source_manifest = read_json(paths.manifest)
    shutil.copyfile(paths.manifest, adapter_dir / "dataset_manifest.json")
    run_manifest = {
        "schema_version": "gemma-adapter-run-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "base_model": BASE_MODEL,
        "base_model_revision": BASE_MODEL_REVISION,
        "adapter_type": config.method,
        "dataset_hash": source_manifest["sft"]["content_hash"],
        "dataset_manifest": "dataset_manifest.json",
        "dataset_summary": {
            "selected_games": source_manifest["selected_game_count"],
            "enriched_games": source_manifest["enriched_game_count"],
            "split_counts": source_manifest["sft"]["split_counts"],
        },
        "trainer": "unsloth",
        "trainer_config": config.as_dict(),
        "gpu": {
            "name": torch.cuda.get_device_properties(0).name,
            "vram_gib": round(gpu["total_gib"], 2),
            "free_vram_gib_at_start": round(gpu["free_gib"], 2),
        },
        "training_metrics": _json_safe(training_result.metrics),
        "validation": validation,
        "git_commit": _git_commit(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("unsloth", "torch", "transformers", "trl", "peft")
        },
    }
    write_json(adapter_dir / "run_manifest.json", run_manifest)
    (adapter_dir / "README.md").write_text(_model_card(config, run_manifest), encoding="utf-8")
    return run_manifest


def push_adapter(
    paths: PipelinePaths,
    method: TrainingMethod,
    repo_prefix: str,
    *,
    private: bool,
    min_legal_rate: float = 0.5,
) -> str:
    adapter_dir = paths.adapter(method)
    required = (
        "adapter_config.json",
        "dataset_manifest.json",
        "run_manifest.json",
        "README.md",
    )
    if not all((adapter_dir / filename).exists() for filename in required):
        raise RuntimeError(f"no saved {method} adapter at {adapter_dir}")
    run_manifest = read_json(adapter_dir / "run_manifest.json")
    validation = run_manifest.get("validation", {})
    if not validation.get("available"):
        raise RuntimeError("refusing to publish an adapter without held-out validation")
    legal_rate = validation.get("legal_move_rate")
    if not isinstance(legal_rate, int | float) or legal_rate < min_legal_rate:
        raise RuntimeError(
            f"held-out legal move rate {legal_rate!r} is below the publish threshold "
            f"{min_legal_rate:.3f}; inspect the run before changing --min-legal-rate"
        )
    repo_id = repository_for(repo_prefix, method)
    api = HfApi()
    api.create_repo(repo_id, repo_type="model", private=private, exist_ok=True)
    api.upload_folder(
        repo_id=repo_id,
        repo_type="model",
        folder_path=adapter_dir,
        commit_message=f"Upload Gemma 4 chess {method.upper()} adapter",
    )
    return f"https://huggingface.co/{repo_id}"


def _validate_adapter(
    model: Any,
    tokenizer: Any,
    FastModel: Any,
    torch: Any,
    paths: PipelinePaths,
    *,
    limit: int,
) -> dict[str, Any]:
    candidates = [row for row in read_jsonl(paths.split("test")) if row["task"] == "move"]
    if not candidates:
        candidates = [row for row in read_jsonl(paths.split("validation")) if row["task"] == "move"]
    candidates = candidates[:limit]
    if not candidates:
        return {"available": False, "reason": "no held-out move rows"}

    FastModel.for_inference(model)
    details = []
    legal_count = json_count = 0
    for row in candidates:
        prompt_messages = row["messages"][:-1]
        inputs = tokenizer.apply_chat_template(
            prompt_messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to("cuda")
        with torch.inference_mode():
            outputs = model.generate(**inputs, max_new_tokens=64, do_sample=False)
        prompt_length = inputs["input_ids"].shape[1]
        raw_reply = tokenizer.decode(outputs[0][prompt_length:], skip_special_tokens=True)
        parsed_move = parse_move_reply(raw_reply)
        json_ok = parsed_move is not None
        legal = parsed_move in row["legal_moves"] if parsed_move else False
        json_count += int(json_ok)
        legal_count += int(legal)
        details.append(
            {
                "row_id": row["row_id"],
                "raw_reply": raw_reply,
                "parsed_move": parsed_move,
                "json_ok": json_ok,
                "legal": legal,
            }
        )
    return {
        "available": True,
        "sample_count": len(candidates),
        "valid_json_rate": json_count / len(candidates),
        "legal_move_rate": legal_count / len(candidates),
        "details": details,
    }


def _model_card(config: TrainerConfig, manifest: dict[str, Any]) -> str:
    validation = manifest["validation"]
    enriched = manifest["dataset_summary"]["enriched_games"]
    metric = (
        f"Held-out legal move rate: {validation['legal_move_rate']:.3f} "
        f"({validation['sample_count']} samples)."
        if validation.get("available")
        else f"Held-out validation unavailable: {validation['reason']}."
    )
    return f"""---
base_model: {BASE_MODEL}
library_name: peft
license: apache-2.0
datasets:
- Lichess/standard-chess-games
tags:
- gemma-4
- chess
- lora
---

# Gemma 4 E2B Chessking ({config.method.upper()})

PEFT adapter trained on a bounded, game-level-split sample of short Lichess
checkmates where the winner captured at most three opposing pieces. The sample
contains {enriched} Luna-enriched games with a concrete real-world mapping and
a video-scene description.

This repository contains an adapter, not a merged model or GGUF. Load it with
the base model named above. The training data uses the checkpoint's own Gemma 4
chat template.

{metric}

The exact source revision, selection rules, dataset hash, training settings,
hardware, package versions, and raw held-out replies are in `run_manifest.json`.
"""


def _git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))
