"""Pure calculations for the adaptation evidence chain: dataset
snapshot identity, the training configuration catalog, evaluation suite
identity, and benchmark reply judging. No I/O here.

The chain this module underpins: frozen dataset (hashed) -> legible
config (hashed) -> adapter whose provenance names both -> frozen eval
suite (hashed) -> benchmark runs for a base and an adapted checkpoint
over that one suite -> a comparison that refuses to produce a delta
unless the frozen identities actually match.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from euro_chess_studio.calculations.evals import compute_position_set_id
from euro_chess_studio.calculations.export import (
    PROMPT_TEMPLATE,
    SFT_PROMPT_VERSION,
    is_training_eligible,
)
from euro_chess_studio.calculations.llm_prompts import analyze_move_reply
from euro_chess_studio.chess.board import get_playable_legal_moves

Row = Any

# Versions the stored row/example formats, not the prompt text (that is
# SFT_PROMPT_VERSION in calculations/export.py).
SNAPSHOT_SCHEMA_VERSION = "sft-prompt-completion-v1"
SUITE_SCHEMA_VERSION = "bench-fen-legal-v1"

# The task recorded on benchmark model_attempts rows. Deliberately not
# "move": organic gameplay metrics filter on task="move", so benchmark
# replies can never pool into them, while the same pure calculations
# run over either task by parameter.
BENCHMARK_TASK = "benchmark_move"

BASE_CHECKPOINT = "base"


class AdaptationError(ValueError):
    """A request that cannot be satisfied honestly: unknown snapshot or
    config, a cached replay asked to pose as training on other data, or
    training data overlapping the held-out suite."""


def compute_content_hash(lines: list[str]) -> str:
    """One deterministic id for a frozen collection: sorted, duplicates
    preserved, first 16 hex chars of the sha256 -- the same recipe as
    compute_position_set_id, for the same reason. Order must not matter;
    multiplicity must."""
    digest = hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()
    return digest[:16]


def compute_snapshot_content_hash(rows: list[dict]) -> str:
    return compute_content_hash([json.dumps(row, sort_keys=True) for row in rows])


def compute_suite_content_hash(
    examples: list[dict], *, prompt_version: str, schema_version: str
) -> str:
    """The suite identity covers the examples and the prompt contract:
    the same positions asked under a different prompt version are a
    different benchmark."""
    lines = [json.dumps(example, sort_keys=True) for example in examples]
    lines.append(f"prompt_version={prompt_version}")
    lines.append(f"schema_version={schema_version}")
    return compute_content_hash(lines)


def compute_config_hash(config: dict) -> str:
    return compute_content_hash([json.dumps(config, sort_keys=True)])


_FEN_LINE = re.compile(r"^Position \(FEN\): (.+)$", re.MULTILINE)


def extract_fen_from_prompt(prompt: str) -> str | None:
    """The FEN a PROMPT_TEMPLATE-shaped prompt asks about. Used to prove
    training rows and held-out suite examples do not overlap."""
    match = _FEN_LINE.search(prompt)
    return match.group(1).strip() if match else None


@dataclass(frozen=True)
class TrainingConfig:
    """A legible training configuration. Names are deliberately exact:
    base_model is the training starting point (unquantized weights),
    inference_repo is the GGUF repository a merged result deploys back
    to, serving_alias is what llama.cpp answers as. TRL or Axolotl never
    trains the GGUF directly."""

    config_id: str
    label: str
    modality: str
    base_model: str
    method: str
    lora_r: int
    lora_alpha: int
    lora_dropout: float
    learning_rate: float
    epochs: int
    batch_size: int
    seed: int
    output_task: str
    target_checkpoint: str
    serving_alias: str
    inference_repo: str
    limitations: str

    def as_dict(self) -> dict:
        return {
            "config_id": self.config_id,
            "label": self.label,
            "modality": self.modality,
            "base_model": self.base_model,
            "method": self.method,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "seed": self.seed,
            "output_task": self.output_task,
            "target_checkpoint": self.target_checkpoint,
            "serving_alias": self.serving_alias,
            "inference_repo": self.inference_repo,
        }

    @property
    def config_hash(self) -> str:
        return compute_config_hash(self.as_dict())


TRAINING_CONFIGS: tuple[TrainingConfig, ...] = (
    TrainingConfig(
        config_id="text-gemma-lora-v1",
        label="Gemma LoRA, move SFT",
        modality="text",
        base_model="google/gemma-4-E2B-it-qat-q4_0-unquantized",
        method="lora",
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        learning_rate=2e-4,
        epochs=3,
        batch_size=8,
        seed=7,
        output_task="FEN plus legal moves to one UCI move as JSON (sft-v2 contract)",
        target_checkpoint="gemma-chess-sft-v1",
        serving_alias="gemma-4-2b-local",
        inference_repo="google/gemma-4-E2B-it-qat-q4_0-gguf",
        limitations=(
            "LoRA adapter over the unquantized weights. Serving it back "
            "through llama.cpp requires merging and converting to GGUF; "
            "the quantized inference repo is never trained directly."
        ),
    ),
)


def get_training_config(config_id: str) -> TrainingConfig:
    for config in TRAINING_CONFIGS:
        if config.config_id == config_id:
            return config
    raise AdaptationError(f"unknown training config: {config_id}")


@dataclass(frozen=True)
class SnapshotBuild:
    """The result of freezing dataset rows into an SFT snapshot."""

    rows: list[dict]
    source_row_ids: list[str]
    row_count: int
    excluded_ineligible_count: int
    source_game_count: int
    source_workspace_count: int
    content_hash: str


def build_snapshot(dataset_rows: list[Row], sft_rows_by_id: dict[str, dict]) -> SnapshotBuild:
    """Combines per-row SFT conversions into one frozen snapshot.

    dataset_rows are fen_legal_moves_to_move rows with move provenance
    (actor, game, workspace); sft_rows_by_id maps a dataset row id to
    its built prompt/completion row, absent when the row was skipped.
    Fallback and unknown actors are counted as excluded rather than
    silently vanishing: the audit archive keeps them, the snapshot does
    not."""
    rows: list[dict] = []
    source_row_ids: list[str] = []
    excluded_ineligible = 0
    games: set[str] = set()
    workspaces: set[str] = set()
    for row in dataset_rows:
        actor = row["move_actor"]
        if not is_training_eligible(actor):
            excluded_ineligible += 1
            continue
        sft_row = sft_rows_by_id.get(row["id"])
        if sft_row is None:
            continue
        rows.append(sft_row)
        source_row_ids.append(row["id"])
        if row["move_game_id"] is not None:
            games.add(row["move_game_id"])
        workspaces.add(row["workspace_id"])
    return SnapshotBuild(
        rows=rows,
        source_row_ids=source_row_ids,
        row_count=len(rows),
        excluded_ineligible_count=excluded_ineligible,
        source_game_count=len(games),
        source_workspace_count=len(workspaces),
        content_hash=compute_snapshot_content_hash(rows),
    )


@dataclass(frozen=True)
class SuiteValidation:
    examples: list[dict]
    content_hash: str
    position_set_id: str


def validate_suite_examples(
    examples: list[dict], *, prompt_version: str, schema_version: str
) -> SuiteValidation:
    """Validation for a frozen suite, semantic as well as structural:
    durable unique example ids, a FEN python-chess actually accepts, a
    legal move list that exactly matches the position (the frozen list
    is the legality judge, so a wrong list would corrupt every score),
    and a rendered prompt that reproduces the declared contract.
    Duplicated FENs are legitimate multiplicity and are preserved in the
    position-set hash."""
    if not examples:
        raise AdaptationError("an evaluation suite needs at least one example")
    if prompt_version != SFT_PROMPT_VERSION:
        raise AdaptationError(
            f"unknown prompt contract {prompt_version!r}: this build renders "
            f"and verifies {SFT_PROMPT_VERSION!r} only"
        )
    seen_ids: set[str] = set()
    for example in examples:
        example_id = example.get("example_id")
        if not isinstance(example_id, str) or not example_id:
            raise AdaptationError("every suite example needs a durable example_id")
        if example_id in seen_ids:
            raise AdaptationError(f"duplicate suite example_id: {example_id}")
        seen_ids.add(example_id)
        fen = example.get("fen")
        if not isinstance(fen, str) or not fen:
            raise AdaptationError(f"suite example {example_id} has no fen")
        try:
            # Playable, not merely parseable: chess.Board accepts a FEN
            # with no black king and generates moves for it.
            derived_legal = sorted(get_playable_legal_moves(fen))
        except ValueError as exc:
            raise AdaptationError(f"suite example {example_id} has an invalid fen: {exc}") from exc
        legal_moves = example.get("legal_moves")
        if not isinstance(legal_moves, list) or not legal_moves:
            raise AdaptationError(f"suite example {example_id} has no legal move list")
        if sorted(legal_moves) != derived_legal:
            raise AdaptationError(
                f"suite example {example_id}'s legal move list does not match "
                "its position; the frozen list is the legality judge and must "
                "be derived, not asserted"
            )
        prompt = example.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise AdaptationError(f"suite example {example_id} has no rendered prompt")
        expected_prompt = PROMPT_TEMPLATE.format(fen=fen, legal_moves=", ".join(legal_moves))
        if prompt != expected_prompt:
            raise AdaptationError(
                f"suite example {example_id}'s prompt does not render the "
                f"declared {prompt_version} contract for its position"
            )
    position_set_id = compute_position_set_id([example["fen"] for example in examples])
    assert position_set_id is not None  # examples is non-empty
    return SuiteValidation(
        examples=examples,
        content_hash=compute_suite_content_hash(
            examples, prompt_version=prompt_version, schema_version=schema_version
        ),
        position_set_id=position_set_id,
    )


def overlapping_fens(snapshot_rows: list[dict], suite_examples: list[dict]) -> list[str]:
    """FENs that appear both in a training snapshot's prompts and in a
    held-out suite. Training-data identity and evaluation-suite identity
    are separate; a non-empty overlap means the comparison would score
    the model on its own training examples."""
    snapshot_fens = {
        fen
        for row in snapshot_rows
        if (fen := extract_fen_from_prompt(row.get("prompt", ""))) is not None
    }
    return sorted({ex["fen"] for ex in suite_examples if ex["fen"] in snapshot_fens})


@dataclass(frozen=True)
class BenchmarkJudgment:
    """How one benchmark reply was judged against its frozen example:
    the same reply analysis organic play uses, with legality decided by
    membership in the example's frozen legal move list (which is exactly
    what the prompt asked for)."""

    parse_ok: bool
    parsed_move: str | None
    is_legal: bool


def judge_benchmark_reply(raw_response: str, legal_moves: list[str]) -> BenchmarkJudgment:
    analysis = analyze_move_reply(raw_response)
    is_legal = analysis.uci is not None and analysis.uci in legal_moves
    return BenchmarkJudgment(
        parse_ok=analysis.parse_ok,
        parsed_move=analysis.move_text,
        is_legal=is_legal,
    )
