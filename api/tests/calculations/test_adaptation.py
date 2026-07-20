"""Tests for the adaptation identity calculations: content hashes that
respect multiplicity, the config catalog, snapshot eligibility, suite
validation, held-out overlap detection, and benchmark reply judging."""

import dataclasses

import chess
import pytest

from euro_chess_studio.calculations.adaptation import (
    SUITE_SCHEMA_VERSION,
    AdaptationError,
    build_snapshot,
    compute_snapshot_content_hash,
    compute_suite_content_hash,
    extract_fen_from_prompt,
    get_training_config,
    judge_benchmark_reply,
    overlapping_fens,
    validate_suite_examples,
)
from euro_chess_studio.calculations.export import PROMPT_TEMPLATE, SFT_PROMPT_VERSION

FEN_A = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
FEN_B = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"


def example(example_id: str, fen: str = FEN_A) -> dict:
    """A semantically valid suite example: real legal moves derived from
    the position, prompt rendered from the actual contract."""
    legal_moves = sorted(move.uci() for move in chess.Board(fen).legal_moves)
    return {
        "example_id": example_id,
        "fen": fen,
        "legal_moves": legal_moves,
        "prompt": PROMPT_TEMPLATE.format(fen=fen, legal_moves=", ".join(legal_moves)),
    }


def test_snapshot_content_hash_is_order_independent_but_multiplicity_sensitive():
    row_a = {"prompt": "p1", "completion": "c1"}
    row_b = {"prompt": "p2", "completion": "c2"}
    assert compute_snapshot_content_hash([row_a, row_b]) == compute_snapshot_content_hash(
        [row_b, row_a]
    )
    assert compute_snapshot_content_hash([row_a]) != compute_snapshot_content_hash([row_a, row_a])


def test_suite_content_hash_covers_the_prompt_contract():
    examples = [example("ex-1")]
    v1 = compute_suite_content_hash(examples, prompt_version="contract-a", schema_version="s1")
    v2 = compute_suite_content_hash(examples, prompt_version="contract-b", schema_version="s1")
    assert v1 != v2


def test_config_hash_changes_with_any_parameter():
    config = get_training_config("text-gemma-lora-v1")
    changed = dataclasses.replace(config, seed=config.seed + 1)
    assert config.config_hash != changed.config_hash


def test_get_training_config_rejects_unknown_ids():
    with pytest.raises(AdaptationError):
        get_training_config("nope")


def test_training_config_keeps_gemma_roles_distinct():
    config = get_training_config("text-gemma-lora-v1")
    # The GGUF repo is for inference, the unquantized repo is the
    # training starting point, and the alias is what llama.cpp serves.
    assert config.base_model == "google/gemma-4-E2B-it-qat-q4_0-unquantized"
    assert config.inference_repo == "google/gemma-4-E2B-it-qat-q4_0-gguf"
    assert config.serving_alias == "gemma-4-2b-local"
    assert config.base_model != config.inference_repo


def dataset_row(row_id: str, actor: str | None, game_id: str | None = "game-1") -> dict:
    return {
        "id": row_id,
        "workspace_id": "ws-1",
        "move_actor": actor,
        "move_game_id": game_id,
    }


def test_build_snapshot_excludes_fallback_and_unknown_actors():
    rows = [
        dataset_row("r1", "participant"),
        dataset_row("r2", "model"),
        dataset_row("r3", "fallback"),
        dataset_row("r4", "unknown"),
    ]
    sft = {
        "r1": {"prompt": "p1", "completion": "c1"},
        "r2": {"prompt": "p2", "completion": "c2"},
        # Even if a conversion exists for an ineligible row, it must not
        # enter the snapshot.
        "r3": {"prompt": "p3", "completion": "c3"},
        "r4": {"prompt": "p4", "completion": "c4"},
    }
    build = build_snapshot(rows, sft)
    assert build.row_count == 2
    assert build.excluded_ineligible_count == 2
    assert build.source_row_ids == ["r1", "r2"]
    assert {row["prompt"] for row in build.rows} == {"p1", "p2"}


def test_build_snapshot_counts_sources():
    rows = [
        dataset_row("r1", "participant", "game-1"),
        dataset_row("r2", "participant", "game-2"),
        dataset_row("r3", "model", "game-1"),
    ]
    sft = {r: {"prompt": r, "completion": "c"} for r in ("r1", "r2", "r3")}
    build = build_snapshot(rows, sft)
    assert build.source_game_count == 2
    assert build.source_workspace_count == 1


def test_validate_suite_rejects_duplicate_example_ids():
    with pytest.raises(AdaptationError, match="duplicate"):
        validate_suite_examples(
            [example("ex-1"), example("ex-1")],
            prompt_version=SFT_PROMPT_VERSION,
            schema_version=SUITE_SCHEMA_VERSION,
        )


def test_validate_suite_rejects_missing_fields():
    broken = example("ex-1")
    broken.pop("legal_moves")
    with pytest.raises(AdaptationError, match="legal move list"):
        validate_suite_examples(
            [broken], prompt_version=SFT_PROMPT_VERSION, schema_version=SUITE_SCHEMA_VERSION
        )


def test_validate_suite_rejects_an_invalid_fen():
    broken = example("ex-1")
    broken["fen"] = "not a position at all"
    with pytest.raises(AdaptationError, match="invalid fen"):
        validate_suite_examples(
            [broken], prompt_version=SFT_PROMPT_VERSION, schema_version=SUITE_SCHEMA_VERSION
        )


def test_validate_suite_rejects_a_parseable_but_impossible_position():
    """chess.Board happily parses a FEN with no black king and still
    generates moves for it; is_valid() is the gate. The reported repro:
    such a position passed validation."""
    kingless = "rnbq1bnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQ - 0 1"
    broken = example("ex-1")
    broken["fen"] = kingless
    broken["legal_moves"] = sorted(move.uci() for move in chess.Board(kingless).legal_moves)
    broken["prompt"] = PROMPT_TEMPLATE.format(
        fen=kingless, legal_moves=", ".join(broken["legal_moves"])
    )
    with pytest.raises(AdaptationError, match="invalid fen"):
        validate_suite_examples(
            [broken], prompt_version=SFT_PROMPT_VERSION, schema_version=SUITE_SCHEMA_VERSION
        )


def test_validate_suite_rejects_a_wrong_legal_move_list():
    # The frozen list is the legality judge; an asserted list that does
    # not match the position would corrupt every score it judges.
    broken = example("ex-1")
    broken["legal_moves"] = ["zzzz", "e2e4"]
    with pytest.raises(AdaptationError, match="does not match"):
        validate_suite_examples(
            [broken], prompt_version=SFT_PROMPT_VERSION, schema_version=SUITE_SCHEMA_VERSION
        )


def test_validate_suite_rejects_a_prompt_that_breaks_the_contract():
    broken = example("ex-1")
    broken["prompt"] = "Answer with your favourite opening."
    with pytest.raises(AdaptationError, match="does not render"):
        validate_suite_examples(
            [broken], prompt_version=SFT_PROMPT_VERSION, schema_version=SUITE_SCHEMA_VERSION
        )


def test_validate_suite_rejects_an_unknown_prompt_contract():
    with pytest.raises(AdaptationError, match="unknown prompt contract"):
        validate_suite_examples(
            [example("ex-1")], prompt_version="sft-v0", schema_version=SUITE_SCHEMA_VERSION
        )


def test_validate_suite_preserves_multiplicity_in_the_position_set():
    once = validate_suite_examples(
        [example("ex-1", FEN_A)],
        prompt_version=SFT_PROMPT_VERSION,
        schema_version=SUITE_SCHEMA_VERSION,
    )
    twice = validate_suite_examples(
        [example("ex-1", FEN_A), example("ex-2", FEN_A)],
        prompt_version=SFT_PROMPT_VERSION,
        schema_version=SUITE_SCHEMA_VERSION,
    )
    # The same position sampled twice is a different measurement, and
    # both the position-set id and the suite hash must say so.
    assert once.position_set_id != twice.position_set_id
    assert once.content_hash != twice.content_hash


def test_extract_fen_from_prompt_round_trips_the_template():
    prompt = PROMPT_TEMPLATE.format(fen=FEN_A, legal_moves="e2e4, d2d4")
    assert extract_fen_from_prompt(prompt) == FEN_A
    assert extract_fen_from_prompt("no fen here") is None


def test_overlapping_fens_finds_training_examples_in_the_suite():
    snapshot_rows = [
        {"prompt": PROMPT_TEMPLATE.format(fen=FEN_A, legal_moves="e2e4"), "completion": "c"},
    ]
    suite = [example("ex-1", FEN_A), example("ex-2", FEN_B)]
    assert overlapping_fens(snapshot_rows, suite) == [FEN_A]
    assert overlapping_fens(snapshot_rows, [example("ex-2", FEN_B)]) == []


def test_judge_benchmark_reply_uses_the_frozen_legal_move_list():
    legal = ["e2e4", "d2d4"]
    clean = judge_benchmark_reply('{"move": "e2e4"}', legal)
    assert clean.parse_ok is True
    assert clean.parsed_move == "e2e4"
    assert clean.is_legal is True

    illegal = judge_benchmark_reply('{"move": "a7a5"}', legal)
    assert illegal.parse_ok is True
    assert illegal.is_legal is False

    san = judge_benchmark_reply('{"move": "Nf3"}', legal)
    assert san.parse_ok is True
    assert san.parsed_move == "nf3"
    assert san.is_legal is False

    prose = judge_benchmark_reply("I would play the king pawn forward.", legal)
    assert prose.parse_ok is False
    assert prose.is_legal is False
