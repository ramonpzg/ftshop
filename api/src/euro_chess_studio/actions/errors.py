"""Shared action-layer error types."""


class WorkspaceNotFoundError(ValueError):
    pass


class UserNotFoundError(ValueError):
    pass


class PageNotFoundError(ValueError):
    pass


class InvalidSnippetError(ValueError):
    pass


class GameAlreadyActiveError(ValueError):
    pass


class NoActiveGameError(ValueError):
    pass


class GameClockExpiredError(ValueError):
    """A move arrived after the clock ran out. The game is already lost."""


class StaleMoveError(ValueError):
    """The board changed since the caller decided which move to apply.
    Raised instead of silently applying a decision made against a
    position that no longer exists."""


class NotYourTurnError(ValueError):
    """Someone tried to move for the color they are not playing in an
    active timed match: a participant moving for the model's color, or
    the model moving for the participant's."""


def turn_conflict_detail(exc: GameClockExpiredError | NotYourTurnError) -> dict[str, str]:
    """The {code, message} body a route hands to HTTPException(detail=...)
    for either of these two 409s. `message` is free-form prose for
    display; `code` is the stable contract a client branches on, so a
    copy edit to the message can never silently change which reaction a
    client takes -- the failure mode this exists to prevent is a route
    returning 409 for two different reasons and a client that used to
    tell them apart by pattern-matching the English sentence."""
    code = "clock_expired" if isinstance(exc, GameClockExpiredError) else "not_your_turn"
    return {"code": code, "message": str(exc)}


class GameNotExpiredError(ValueError):
    """A timeout was claimed while the clock still had time on it."""


class InvalidTimeLimitError(ValueError):
    pass


class InvalidOpponentModelError(ValueError):
    pass


class ModelReplyError(RuntimeError):
    """The model answered, but not with anything usable."""


class JobInProgressError(RuntimeError):
    """A single-flight job was asked to start while the same job is
    already running. The duplicate would spend provider money twice for
    one answer, so the refusal is the correct result, not a failure."""


class ScenarioNotFoundError(ValueError):
    pass


class ScenarioReviewError(ValueError):
    """A review that cannot apply: failed suggestion or empty fields."""
