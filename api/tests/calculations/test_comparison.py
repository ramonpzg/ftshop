"""Tests for the base-versus-adapted comparison: signed deltas with
direction-aware verdicts when identities match, explicit refusals when
they do not. A refusal is a result, never a silent blank."""

from euro_chess_studio.calculations.comparison import (
    build_example_comparisons,
    check_run_comparability,
    compare_metric_rows,
)


def metric_row(
    metric: str,
    value: float,
    *,
    position_set_id: str | None = "pset-1",
    version: str = "1",
    direction: str = "higher_is_better",
    unit: str = "ratio",
    numerator: int = 1,
    denominator: int = 2,
) -> dict:
    return {
        "metric": metric,
        "value": value,
        "position_set_id": position_set_id,
        "version": version,
        "direction": direction,
        "unit": unit,
        "numerator": numerator,
        "denominator": denominator,
        "definition": f"{metric} definition",
    }


def run_row(
    *,
    suite_id: str = "suite-1",
    suite_content_hash: str = "hash-1",
    prompt_version: str = "sft-v1",
    model: str = "gemma-4-2b-local",
) -> dict:
    return {
        "suite_id": suite_id,
        "suite_content_hash": suite_content_hash,
        "prompt_version": prompt_version,
        "model": model,
    }


def test_matching_identities_produce_signed_deltas_and_verdicts():
    base = [
        metric_row("model_legal_move_rate", 0.5),
        metric_row("explanation_rate", 0.75),
    ]
    adapted = [
        metric_row("model_legal_move_rate", 1.0),
        metric_row("explanation_rate", 0.0),
    ]
    comparisons = compare_metric_rows(base, adapted)
    by_metric = {c.metric: c for c in comparisons}
    legal = by_metric["model_legal_move_rate"]
    assert legal.comparable is True
    assert legal.delta == 0.5
    assert legal.verdict == "improved"
    explanation = by_metric["explanation_rate"]
    assert explanation.comparable is True
    assert explanation.delta == -0.75
    assert explanation.verdict == "regressed"


def test_lower_is_better_inverts_the_verdict():
    base = [metric_row("flicker", 0.4, direction="lower_is_better")]
    adapted = [metric_row("flicker", 0.2, direction="lower_is_better")]
    (comparison,) = compare_metric_rows(base, adapted)
    assert comparison.delta == -0.2
    assert comparison.verdict == "improved"


def test_equal_values_are_unchanged():
    (comparison,) = compare_metric_rows(
        [metric_row("m", 0.5)],
        [metric_row("m", 0.5)],
    )
    assert comparison.verdict == "unchanged"
    assert comparison.delta == 0


def test_mismatched_position_sets_refuse_a_delta():
    base = [metric_row("m", 0.5, position_set_id="pset-1")]
    adapted = [metric_row("m", 1.0, position_set_id="pset-2")]
    (comparison,) = compare_metric_rows(base, adapted)
    assert comparison.comparable is False
    assert comparison.delta is None
    assert comparison.verdict is None
    assert "different position sets" in comparison.reason
    # Both values stay visible; the refusal is the comparison.
    assert comparison.base_value == 0.5
    assert comparison.adapted_value == 1.0


def test_null_position_set_refuses_a_delta():
    base = [metric_row("m", 0.5, position_set_id=None)]
    adapted = [metric_row("m", 1.0)]
    (comparison,) = compare_metric_rows(base, adapted)
    assert comparison.comparable is False
    assert "missing its frozen position set" in comparison.reason


def test_version_mismatch_refuses_a_delta():
    base = [metric_row("m", 0.5, version="1")]
    adapted = [metric_row("m", 0.6, version="2")]
    (comparison,) = compare_metric_rows(base, adapted)
    assert comparison.comparable is False
    assert "definition version" in comparison.reason


def test_missing_side_refuses_a_delta():
    (comparison,) = compare_metric_rows([metric_row("m", 0.5)], [])
    assert comparison.comparable is False
    assert comparison.reason == "no adapted result for this metric"
    assert comparison.base_value == 0.5
    assert comparison.adapted_value is None


def test_run_level_reason_forces_every_metric_to_not_comparable():
    base = [metric_row("m", 0.5)]
    adapted = [metric_row("m", 1.0)]
    comparisons = compare_metric_rows(
        base, adapted, run_level_reason="the prompt contract differs between runs"
    )
    assert all(not c.comparable for c in comparisons)
    assert comparisons[0].reason == "the prompt contract differs between runs"
    assert comparisons[0].base_value == 0.5


def test_check_run_comparability_flags_suite_and_prompt_mismatches():
    ok = check_run_comparability(run_row(), run_row())
    assert ok.comparable is True

    different_hash = check_run_comparability(run_row(), run_row(suite_content_hash="hash-2"))
    assert different_hash.comparable is False
    assert any("content hash" in reason for reason in different_hash.reasons)

    different_prompt = check_run_comparability(run_row(), run_row(prompt_version="sft-v2"))
    assert different_prompt.comparable is False
    assert any("prompt contract" in reason for reason in different_prompt.reasons)


def test_check_run_comparability_refuses_a_cross_model_pair():
    """A live run of whatever model the room has configured is its own
    evidence; against an adapter of a different base it is not a
    before/after. Same suite, same contract, still not a pair."""
    crossed = check_run_comparability(run_row(model="gpt-5.6-luna"), run_row())
    assert crossed.comparable is False
    assert any("different models" in reason for reason in crossed.reasons)
    assert any("gpt-5.6-luna" in reason for reason in crossed.reasons)


def attempt_row(example_id: str, *, parsed: str | None, legal: int | None, source: str) -> dict:
    return {
        "suite_example_id": example_id,
        "status": "scored",
        "raw_response": f"reply for {example_id}",
        "parsed_move": parsed,
        "is_legal": legal,
        "reply_source": source,
    }


def test_example_comparisons_pair_replies_by_durable_id():
    examples = [
        {"example_id": "ex-1", "fen": "fen-1", "prompt": "p1"},
        {"example_id": "ex-2", "fen": "fen-2", "prompt": "p2"},
    ]
    base = [attempt_row("ex-1", parsed="e2e4", legal=0, source="replayed")]
    adapted = [
        attempt_row("ex-1", parsed="d2d4", legal=1, source="replayed"),
        attempt_row("ex-2", parsed="g1f3", legal=1, source="replayed"),
    ]
    pairs = build_example_comparisons(examples, base, adapted)
    assert pairs[0]["base"]["parsed_move"] == "e2e4"
    assert pairs[0]["base"]["is_legal"] is False
    assert pairs[0]["adapted"]["parsed_move"] == "d2d4"
    assert pairs[0]["adapted"]["is_legal"] is True
    # A missing side is None, not a fabricated reply.
    assert pairs[1]["base"] is None
    assert pairs[1]["adapted"]["parsed_move"] == "g1f3"
