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


class GameNotExpiredError(ValueError):
    """A timeout was claimed while the clock still had time on it."""


class InvalidTimeLimitError(ValueError):
    pass


class InvalidOpponentModelError(ValueError):
    pass


class ModelReplyError(RuntimeError):
    """The model answered, but not with anything usable."""


class ScenarioNotFoundError(ValueError):
    pass


class ScenarioReviewError(ValueError):
    """A review that cannot apply: failed suggestion or empty fields."""
