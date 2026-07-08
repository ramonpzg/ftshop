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


class GameNotExpiredError(ValueError):
    """A timeout was claimed while the clock still had time on it."""


class InvalidTimeLimitError(ValueError):
    pass


class InvalidOpponentModelError(ValueError):
    pass
