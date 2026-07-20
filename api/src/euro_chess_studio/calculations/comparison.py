"""Pure base-versus-adapted benchmark comparison. Given plain rows, no
I/O.

A delta only exists when both results provably measured the same thing:
same suite content hash, same prompt contract, same model lineage
(before and after must be the same model, differing by checkpoint --
a live run of some other configured model is its own evidence, not a
fine-tuning pair), same metric definition version, and the same
non-null position-set id on both rows. Anything else is an explicit
"not comparable" with the reason, never a number that looks like
evidence.
"""

from dataclasses import dataclass
from typing import Any

Row = Any

# Metrics in teaching order: the adaptation target first, then format,
# then the trade-off metric that regresses.
METRIC_ORDER = ("model_legal_move_rate", "valid_json_rate", "explanation_rate")


@dataclass(frozen=True)
class RunComparability:
    comparable: bool
    reasons: tuple[str, ...]


def check_run_comparability(base_run: Row, adapted_run: Row) -> RunComparability:
    """Whether two benchmark runs measured the same frozen contract on
    the same model lineage."""
    reasons: list[str] = []
    if base_run["suite_id"] != adapted_run["suite_id"]:
        reasons.append("the runs used different evaluation suites")
    elif base_run["suite_content_hash"] != adapted_run["suite_content_hash"]:
        reasons.append("the evaluation suite content hash differs between runs")
    if base_run["prompt_version"] != adapted_run["prompt_version"]:
        reasons.append("the prompt contract differs between runs")
    if base_run["model"] != adapted_run["model"]:
        reasons.append(
            "the runs used different models "
            f"({base_run['model']} vs {adapted_run['model']}); a "
            "fine-tuning delta needs the adapter's own base model on "
            "both sides, and a run of another configured model is its "
            "own evidence, not a before"
        )
    return RunComparability(comparable=not reasons, reasons=tuple(reasons))


@dataclass(frozen=True)
class MetricComparison:
    metric: str
    comparable: bool
    reason: str | None
    base_value: float | None
    adapted_value: float | None
    delta: float | None
    verdict: str | None
    unit: str | None
    direction: str | None
    base_numerator: int | None
    base_denominator: int | None
    adapted_numerator: int | None
    adapted_denominator: int | None
    definition: str | None
    version: str | None
    position_set_id: str | None


def _not_comparable(
    metric: str, reason: str, base: Row | None, adapted: Row | None
) -> "MetricComparison":
    either = base if base is not None else adapted
    return MetricComparison(
        metric=metric,
        comparable=False,
        reason=reason,
        base_value=base["value"] if base is not None else None,
        adapted_value=adapted["value"] if adapted is not None else None,
        delta=None,
        verdict=None,
        unit=either["unit"] if either is not None else None,
        direction=either["direction"] if either is not None else None,
        base_numerator=base["numerator"] if base is not None else None,
        base_denominator=base["denominator"] if base is not None else None,
        adapted_numerator=adapted["numerator"] if adapted is not None else None,
        adapted_denominator=adapted["denominator"] if adapted is not None else None,
        definition=either["definition"] if either is not None else None,
        version=either["version"] if either is not None else None,
        position_set_id=None,
    )


def _verdict(delta: float, direction: str) -> str:
    if delta == 0:
        return "unchanged"
    if direction == "lower_is_better":
        return "improved" if delta < 0 else "regressed"
    return "improved" if delta > 0 else "regressed"


def compare_metric_rows(
    base_rows: list[Row],
    adapted_rows: list[Row],
    *,
    run_level_reason: str | None = None,
) -> list[MetricComparison]:
    """Pairs one run's metric rows with another's by metric name and
    decides, per metric, whether a signed delta is honest. A run-level
    reason (mismatched suite hash or prompt contract) forces every pair
    to not-comparable while keeping both values visible: the refusal is
    the result, not a blank screen."""
    base_by_metric = {row["metric"]: row for row in base_rows}
    adapted_by_metric = {row["metric"]: row for row in adapted_rows}
    ordered = [m for m in METRIC_ORDER if m in base_by_metric or m in adapted_by_metric]
    ordered += sorted(
        (set(base_by_metric) | set(adapted_by_metric)) - set(ordered),
    )

    comparisons: list[MetricComparison] = []
    for metric in ordered:
        base = base_by_metric.get(metric)
        adapted = adapted_by_metric.get(metric)
        if run_level_reason is not None:
            comparisons.append(_not_comparable(metric, run_level_reason, base, adapted))
            continue
        if base is None:
            comparisons.append(
                _not_comparable(metric, "no base result for this metric", base, adapted)
            )
            continue
        if adapted is None:
            comparisons.append(
                _not_comparable(metric, "no adapted result for this metric", base, adapted)
            )
            continue
        if base["version"] != adapted["version"]:
            comparisons.append(
                _not_comparable(metric, "the metric definition version differs", base, adapted)
            )
            continue
        if base["direction"] != adapted["direction"] or base["unit"] != adapted["unit"]:
            comparisons.append(
                _not_comparable(metric, "the metric unit or direction differs", base, adapted)
            )
            continue
        if base["position_set_id"] is None or adapted["position_set_id"] is None:
            comparisons.append(
                _not_comparable(
                    metric, "a result is missing its frozen position set", base, adapted
                )
            )
            continue
        if base["position_set_id"] != adapted["position_set_id"]:
            comparisons.append(
                _not_comparable(
                    metric,
                    "the runs measured different position sets "
                    f"({base['position_set_id']} vs {adapted['position_set_id']})",
                    base,
                    adapted,
                )
            )
            continue
        delta = adapted["value"] - base["value"]
        comparisons.append(
            MetricComparison(
                metric=metric,
                comparable=True,
                reason=None,
                base_value=base["value"],
                adapted_value=adapted["value"],
                delta=delta,
                verdict=_verdict(delta, base["direction"]),
                unit=base["unit"],
                direction=base["direction"],
                base_numerator=base["numerator"],
                base_denominator=base["denominator"],
                adapted_numerator=adapted["numerator"],
                adapted_denominator=adapted["denominator"],
                definition=base["definition"],
                version=base["version"],
                position_set_id=base["position_set_id"],
            )
        )
    return comparisons


def _reply_view(attempt: Row | None) -> dict | None:
    if attempt is None:
        return None
    return {
        "status": attempt["status"],
        "raw_response": attempt["raw_response"],
        "parsed_move": attempt["parsed_move"],
        "is_legal": None if attempt["is_legal"] is None else bool(attempt["is_legal"]),
        "reply_source": attempt["reply_source"],
    }


def build_example_comparisons(
    examples: list[dict],
    base_attempts: list[Row],
    adapted_attempts: list[Row],
) -> list[dict]:
    """Per-example before/after evidence: the frozen input alongside the
    judged base and adapted replies, paired by durable example id."""
    base_by_example = {a["suite_example_id"]: a for a in base_attempts}
    adapted_by_example = {a["suite_example_id"]: a for a in adapted_attempts}
    return [
        {
            "example_id": example["example_id"],
            "fen": example["fen"],
            "prompt": example["prompt"],
            "base": _reply_view(base_by_example.get(example["example_id"])),
            "adapted": _reply_view(adapted_by_example.get(example["example_id"])),
        }
        for example in examples
    ]
