"""Pure eval metric calculations. Given plain data, no I/O.

Every metric returns a MetricResult that says what was measured, over
what, and how: numerator, denominator, unit, direction, definition,
version, the scope filters that produced the sample, and the exact
row ids that made up the sample (the frozen input set, auditable after
the fact rather than re-derived from whatever the tables contain
later). An empty sample is an explicit unavailable result, never a
zero or a perfect score.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from euro_chess_studio.calculations.llm_prompts import extract_json_object

# Each row is a dict or sqlite3.Row -- anything indexable by column name.
Row = Any

LEGAL_MOVE_RATE_VERSION = "2"
MODEL_LEGAL_MOVE_RATE_VERSION = "1"
VALID_JSON_RATE_VERSION = "2"


@dataclass(frozen=True)
class MetricResult:
    metric: str
    available: bool
    value: float | None
    numerator: int
    denominator: int
    definition: str
    version: str
    unit: str = "ratio"
    direction: str = "higher_is_better"
    scope: dict = field(default_factory=dict)
    # The id of every row in the denominator: the exact frozen input set
    # this value was computed from.
    sample_ids: tuple[str, ...] = ()


def _unavailable(metric: str, definition: str, version: str, scope: dict) -> MetricResult:
    return MetricResult(
        metric=metric,
        available=False,
        value=None,
        numerator=0,
        denominator=0,
        definition=definition,
        version=version,
        scope=scope,
    )


def compute_legal_move_rate(moves: Sequence[Row], *, actor: str = "participant") -> MetricResult:
    """Share of one actor's recorded move attempts that were legal.

    Filters by the actor column, so participant fumbling never counts
    for or against the model. Rows migrated from before provenance
    existed carry actor 'unknown' and are excluded from every scope.
    """
    definition = f"legal moves / recorded move attempts by actor '{actor}'"
    scope = {"actor": actor}
    sample = [move for move in moves if move["actor"] == actor]
    if not sample:
        return _unavailable("legal_move_rate", definition, LEGAL_MOVE_RATE_VERSION, scope)
    legal = sum(1 for move in sample if move["is_legal"])
    return MetricResult(
        metric="legal_move_rate",
        available=True,
        value=legal / len(sample),
        numerator=legal,
        denominator=len(sample),
        definition=definition,
        version=LEGAL_MOVE_RATE_VERSION,
        scope=scope,
        sample_ids=tuple(move["id"] for move in sample),
    )


def compute_model_legal_move_rate(
    attempts: Sequence[Row],
    *,
    model: str | None = None,
    game_id: str | None = None,
    checkpoint: str | None = None,
) -> MetricResult:
    """Share of received model replies that contained a legal move.

    The sample is move-task attempts by actor 'model' that produced a
    reply at all; transport failures are not the model's answer and stay
    out of the denominator. Every retry counts as its own attempt.
    Fallback moves have actor 'fallback' and never enter this metric.

    model and checkpoint scope the sample to one version so a base and
    an adapted model's results can be computed, stored, and compared
    side by side instead of one overwriting the other.
    """
    definition = "attempts whose reply parsed to a legal move / model replies received (task=move)"
    scope: dict = {"task": "move", "actor": "model"}
    if model is not None:
        scope["model"] = model
    if game_id is not None:
        scope["game_id"] = game_id
    if checkpoint is not None:
        scope["checkpoint"] = checkpoint

    sample = [
        attempt
        for attempt in attempts
        if attempt["task"] == "move"
        and attempt["actor"] == "model"
        and attempt["raw_response"] is not None
        and (model is None or attempt["model"] == model)
        and (game_id is None or attempt["game_id"] == game_id)
        and (checkpoint is None or attempt["checkpoint"] == checkpoint)
    ]
    if not sample:
        return _unavailable(
            "model_legal_move_rate", definition, MODEL_LEGAL_MOVE_RATE_VERSION, scope
        )
    legal = sum(1 for attempt in sample if attempt["is_legal"] == 1)
    return MetricResult(
        metric="model_legal_move_rate",
        available=True,
        value=legal / len(sample),
        numerator=legal,
        denominator=len(sample),
        definition=definition,
        version=MODEL_LEGAL_MOVE_RATE_VERSION,
        scope=scope,
        sample_ids=tuple(attempt["id"] for attempt in sample),
    )


def compute_valid_json_rate(
    attempts: Sequence[Row], *, task: str | None = None, model: str | None = None
) -> MetricResult:
    """Share of raw model replies that parsed as a JSON object.

    Measured over attempts where the task asked for JSON and a reply
    arrived, by parsing the stored raw reply with the same extractor the
    app uses to consume replies. This is raw model output, not the
    application's own serialization. An optional model filter lets a
    base and an adapted model's rates coexist rather than blend.
    """
    definition = "raw replies parsing as a JSON object / replies received where JSON was asked"
    scope: dict = {"json_requested": True}
    if task is not None:
        scope["task"] = task
    if model is not None:
        scope["model"] = model

    sample = [
        attempt
        for attempt in attempts
        if attempt["json_requested"]
        and attempt["raw_response"] is not None
        and (task is None or attempt["task"] == task)
        and (model is None or attempt["model"] == model)
    ]
    if not sample:
        return _unavailable("valid_json_rate", definition, VALID_JSON_RATE_VERSION, scope)
    valid = sum(1 for attempt in sample if extract_json_object(attempt["raw_response"]) is not None)
    return MetricResult(
        metric="valid_json_rate",
        available=True,
        value=valid / len(sample),
        numerator=valid,
        denominator=len(sample),
        definition=definition,
        version=VALID_JSON_RATE_VERSION,
        scope=scope,
        sample_ids=tuple(attempt["id"] for attempt in sample),
    )
