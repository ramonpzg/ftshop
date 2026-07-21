"""Command line entry point for the complete chess adaptation run."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from euro_chess_studio.data.llm_client import video_prompt_chat

from chess_adapt.actions.pipeline import enrich_sample, prepare_sample
from chess_adapt.actions.training import preflight_training, push_adapter, train_adapter
from chess_adapt.calculations.dataset import SelectionConfig
from chess_adapt.calculations.training import (
    DEFAULT_REPO_PREFIX,
    TrainerConfig,
    TrainingMethod,
)
from chess_adapt.data.store import PipelinePaths, pipeline_lock

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPO_ROOT / "data/processed/text/lichess-low-capture"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts/generated/chess-adapt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chess-adapt",
        description=(
            "Prepare a bounded Lichess sample, enrich it through Luna, train Gemma 4 "
            "LoRA/QLoRA adapters with Unsloth, and publish the saved adapters."
        ),
    )
    stages = parser.add_argument_group("stages")
    stages.add_argument(
        "--all",
        action="store_true",
        help="run prepare, enrich, QLoRA, and push (the viable 8 GB laptop path)",
    )
    stages.add_argument("--prepare", action="store_true", help="download/filter/save the sample")
    stages.add_argument("--enrich", action="store_true", help="add resumable Luna mappings")
    stages.add_argument("--qlora", action="store_true", help="train the 4-bit QLoRA adapter")
    stages.add_argument(
        "--lora",
        action="store_true",
        help="train the bf16 LoRA adapter (requires at least 16 GiB VRAM)",
    )
    stages.add_argument("--push", action="store_true", help="publish each selected adapter")

    data = parser.add_argument_group("sample")
    data.add_argument("--limit", type=int, default=64, help="number of selected games")
    data.add_argument("--scan-limit", type=int, default=121_332)
    data.add_argument("--max-plies", type=int, default=60)
    data.add_argument("--max-winner-captures", type=int, default=3)
    data.add_argument("--split-seed", type=int, default=2026)
    data.add_argument(
        "--enrich-limit",
        type=int,
        help="maximum new Luna calls this invocation; successes already on disk are skipped",
    )
    data.add_argument("--offline", action="store_true", help="require the source Parquet in cache")
    data.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    data.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)

    train = parser.add_argument_group("training")
    train.add_argument("--max-steps", type=int, default=60)
    train.add_argument("--max-seq-length", type=int, default=1_024)
    train.add_argument("--rank", type=int, default=8)
    train.add_argument("--alpha", type=int, default=8)
    train.add_argument("--learning-rate", type=float, default=2e-4)
    train.add_argument("--gradient-accumulation-steps", type=int, default=8)
    train.add_argument("--eval-samples", type=int, default=8)
    train.add_argument("--overwrite", action="store_true")
    train.add_argument(
        "--force-vram",
        action="store_true",
        help="bypass the local VRAM guard; it does not make an undersized GPU work",
    )

    publish = parser.add_argument_group("publishing")
    publish.add_argument("--repo-prefix", default=DEFAULT_REPO_PREFIX)
    publish.add_argument("--min-legal-rate", type=float, default=0.5)
    publish.add_argument("--private", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        _main(argv)
    except (RuntimeError, ValueError) as exc:
        if os.environ.get("CHESS_ADAPT_DEBUG") == "1":
            raise
        print(f"chess-adapt: {exc}", file=sys.stderr)
        return 1
    return 0


def _main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if not any((args.all, args.prepare, args.enrich, args.qlora, args.lora, args.push)):
        args.all = True

    paths = PipelinePaths(data_dir=args.data_dir.resolve(), output_dir=args.output_dir.resolve())
    with pipeline_lock(paths):
        _run(args, paths)


def _run(args: argparse.Namespace, paths: PipelinePaths) -> None:
    methods: list[TrainingMethod] = []
    if args.all or args.qlora:
        methods.append("qlora")
    if args.lora:
        methods.append("lora")
    if args.push and not methods:
        methods.append("qlora")

    if args.all or args.qlora or args.lora:
        for method in methods:
            gpu = preflight_training(method, force_vram=args.force_vram)
            print(
                f"GPU preflight for {method.upper()}: {gpu['name']}, "
                f"{gpu['free_gib']:.1f}/{gpu['total_gib']:.1f} GiB free"
            )

    selection = SelectionConfig(
        limit=args.limit,
        scan_limit=args.scan_limit,
        max_plies=args.max_plies,
        max_winner_captures=args.max_winner_captures,
        split_seed=args.split_seed,
    )

    if args.all or args.prepare:
        print("Preparing bounded Lichess sample")
        summary = prepare_sample(paths, selection, offline=args.offline)
        print(f"Selected {summary.selected} games after scanning {summary.scanned}")
        print(summary.games_path)

    if args.all or args.enrich:
        print("Enriching games through the video_prompt Chat Completions profile")
        summary = enrich_sample(
            paths,
            _enrich_one,
            split_seed=args.split_seed,
            limit=args.enrich_limit,
        )
        print(
            f"Enrichment: {summary.succeeded} succeeded, {summary.failed} failed, "
            f"{summary.already_succeeded} already complete"
        )
        if summary.stopped_after_failures:
            raise RuntimeError(
                "enrichment stopped after three consecutive failures; fix the endpoint and rerun. "
                "Successful replies are already saved."
            )

    for method in methods:
        if args.all or args.qlora or args.lora:
            print(f"Training {method.upper()} adapter")
            run = train_adapter(
                paths,
                TrainerConfig(
                    method=method,
                    max_seq_length=args.max_seq_length,
                    rank=args.rank,
                    alpha=args.alpha,
                    learning_rate=args.learning_rate,
                    gradient_accumulation_steps=args.gradient_accumulation_steps,
                    max_steps=args.max_steps,
                    eval_samples=args.eval_samples,
                ),
                overwrite=args.overwrite,
                force_vram=args.force_vram,
            )
            validation = run["validation"]
            if validation.get("available"):
                print(
                    f"Held-out legal move rate: {validation['legal_move_rate']:.3f} "
                    f"on {validation['sample_count']} rows"
                )
        if args.all or args.push:
            print(f"Publishing {method.upper()} adapter")
            print(
                push_adapter(
                    paths,
                    method,
                    args.repo_prefix,
                    private=args.private,
                    min_legal_rate=args.min_legal_rate,
                )
            )


def _enrich_one(messages: list[dict[str, str]]) -> dict:
    outcome = video_prompt_chat(messages, json_response=True, timeout=120.0)
    return {
        "raw_reply": outcome.content,
        "model": outcome.model,
        "provider_alias": outcome.provider_alias,
        "transport_attempts": outcome.attempts,
        "request_ids": list(outcome.request_ids),
        "json_mode_requested": outcome.json_mode_requested,
        "json_mode_sent": outcome.json_mode_sent,
        "json_mode_dropped": outcome.json_mode_dropped,
        "reasoning_effort_dropped": outcome.reasoning_effort_dropped,
    }


if __name__ == "__main__":
    main()
