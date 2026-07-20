"""Pure eval metric calculations. Given plain data, no I/O.

Every metric returns a MetricResult that says what was measured, over
what, and how: numerator, denominator, unit, direction, definition,
version, the scope filters that produced the sample, the exact row ids
that made up the sample (an audit trail back to moves/model_attempts),
and the exact input positions (FENs) those rows were about. The
positions are the actual frozen input set: two eval runs -- a base
model and an adapted one, or the same model on two different days --
can only be compared honestly if they measured the same positions, and
compute_position_set_id turns that set into one deterministic id so
two runs can prove they match (or prove they don't) instead of asking
a reader to trust that two separately-filtered queries happened to
cover the same ground. An empty sample is an explicit unavailable
result, never a zero or a perfect score.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from euro_chess_studio.calculations.llm_prompts import extract_json_object, has_explanation_field

# Each row is a dict or sqlite3.Row -- anything indexable by column name.
Row = Any

LEGAL_MOVE_RATE_VERSION = "2"
MODEL_LEGAL_MOVE_RATE_VERSION = "1"
VALID_JSON_RATE_VERSION = "2"
# v2: counts the contract's optional "why" field instead of prose
# outside the JSON, which the contract forbids and v1 wrongly rewarded.
EXPLANATION_RATE_VERSION = "2"


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
    # The id of every row in the denominator: an audit trail back to the
    # moves/model_attempts rows, not itself a stable cross-model identity
    # (two different models produce two different sets of row ids even
    # over the identical position).
    sample_ids: tuple[str, ...] = ()
    # The fen of every row in the denominator, in sample order. This is
    # the actual input the metric measured over; compute_position_set_id
    # turns it into one id two runs can compare.
    positions: tuple[str, ...] = ()


def compute_position_set_id(positions: Sequence[str | None]) -> str | None:
    """A deterministic id for the exact multiset of input positions
    sampled: order-independent (the same positions in a different order
    hash the same), but deliberately NOT duplicate-independent. Every
    repeated attempt is a separate row in the denominator, so a position
    sampled once and the same position sampled a hundred times are
    different measurements, not the same evaluation wearing a different
    denominator -- collapsing them to the same id would let a sample
    with wildly different repeat structure claim to be identical to one
    with none. Two eval results with matching ids were measured over
    the identical positions in the identical proportions; a mismatch
    means they were not, no matter how similar their scope looks
    otherwise. None for an empty set -- there is no position set to
    identify."""
    present = sorted(position for position in positions if position is not None)
    if not present:
        return None
    digest = hashlib.sha256("\n".join(present).encode()).hexdigest()
    return digest[:16]


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
        positions=tuple(move["fen_before"] for move in sample),
    )


def compute_model_legal_move_rate(
    attempts: Sequence[Row],
    *,
    model: str | None = None,
    game_id: str | None = None,
    checkpoint: str | None = None,
    task: str = "move",
) -> MetricResult:
    """Share of received model replies that contained a legal move.

    The sample is one task's attempts by actor 'model' that produced a
    reply at all; transport failures are not the model's answer and stay
    out of the denominator. Every retry counts as its own attempt.
    Fallback moves have actor 'fallback' and never enter this metric.

    The task defaults to organic game moves; the benchmark runner passes
    'benchmark_move' so the same calculation scores frozen-suite replies
    without ever pooling them with live gameplay.

    model and checkpoint scope the sample to one version so a base and
    an adapted model's results can be computed, stored, and compared
    side by side instead of one overwriting the other.
    """
    definition = (
        f"attempts whose reply parsed to a legal move / model replies received (task={task})"
    )
    scope: dict = {"task": task, "actor": "model"}
    if model is not None:
        scope["model"] = model
    if game_id is not None:
        scope["game_id"] = game_id
    if checkpoint is not None:
        scope["checkpoint"] = checkpoint

    sample = [
        attempt
        for attempt in attempts
        if attempt["task"] == task
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
        positions=tuple(attempt["fen"] for attempt in sample),
    )


def compute_valid_json_rate(
    attempts: Sequence[Row],
    *,
    task: str | None = None,
    model: str | None = None,
    checkpoint: str | None = None,
) -> MetricResult:
    """Share of raw model replies that parsed as a JSON object.

    Measured over attempts where the task asked for JSON and a reply
    arrived, by parsing the stored raw reply with the same extractor the
    app uses to consume replies. This is raw model output, not the
    application's own serialization. Optional model and checkpoint
    filters let a base and an adapted checkpoint's rates coexist rather
    than blend: without a checkpoint filter, one model with two
    checkpoints in play would silently pool both checkpoints' attempts
    into a single unscoped number.
    """
    definition = "raw replies parsing as a JSON object / replies received where JSON was asked"
    scope: dict = {"json_requested": True}
    if task is not None:
        scope["task"] = task
    if model is not None:
        scope["model"] = model
    if checkpoint is not None:
        scope["checkpoint"] = checkpoint

    sample = [
        attempt
        for attempt in attempts
        if attempt["json_requested"]
        and attempt["raw_response"] is not None
        and (task is None or attempt["task"] == task)
        and (model is None or attempt["model"] == model)
        and (checkpoint is None or attempt["checkpoint"] == checkpoint)
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
        positions=tuple(attempt["fen"] for attempt in sample),
    )


def compute_explanation_rate(
    attempts: Sequence[Row],
    *,
    task: str | None = None,
    model: str | None = None,
    checkpoint: str | None = None,
) -> MetricResult:
    """Share of received replies whose JSON carries the optional "why"
    explanation the sft-v2 contract invites.

    Higher is better for a model meant to teach, and legitimately so:
    the explanation lives inside the JSON the prompt asks for, so a
    reply cannot score here by breaking the format. This is the
    workshop's honest trade-off metric -- an adapter trained on
    bare-completion pairs gets better at legality and format while this
    number falls, because nothing in the training data filled the why
    field.
    """
    definition = 'replies whose JSON includes a non-empty "why" field / replies received'
    scope: dict = {}
    if task is not None:
        scope["task"] = task
    if model is not None:
        scope["model"] = model
    if checkpoint is not None:
        scope["checkpoint"] = checkpoint

    sample = [
        attempt
        for attempt in attempts
        if attempt["raw_response"] is not None
        and (task is None or attempt["task"] == task)
        and (model is None or attempt["model"] == model)
        and (checkpoint is None or attempt["checkpoint"] == checkpoint)
    ]
    if not sample:
        return _unavailable("explanation_rate", definition, EXPLANATION_RATE_VERSION, scope)
    explained = sum(1 for attempt in sample if has_explanation_field(attempt["raw_response"]))
    return MetricResult(
        metric="explanation_rate",
        available=True,
        value=explained / len(sample),
        numerator=explained,
        denominator=len(sample),
        definition=definition,
        version=EXPLANATION_RATE_VERSION,
        scope=scope,
        sample_ids=tuple(attempt["id"] for attempt in sample),
        positions=tuple(attempt["fen"] for attempt in sample),
    )
