"""Pure ID helpers. No I/O, no side effects."""

import uuid


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"
