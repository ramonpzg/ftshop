"""Pure ID helpers. No I/O, no side effects."""

import uuid


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def workspace_shape_id(user_id: str, page_slug: str) -> str:
    """Deterministic tldraw shape id for a user's workspace on a page.

    Must match web/src/calculations/ids.ts workspaceShapeId exactly: the
    frontend creates the tldraw shape using this id verbatim.
    """
    return f"shape:workspace-{user_id}-{page_slug}"
