"""Shared action-layer error types."""


class WorkspaceNotFoundError(ValueError):
    pass


class UserNotFoundError(ValueError):
    pass


class PageNotFoundError(ValueError):
    pass


class InvalidSnippetError(ValueError):
    pass
