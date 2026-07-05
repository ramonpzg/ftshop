"""Pure eval metric calculations. Given plain data, no I/O."""

import json
from collections.abc import Sequence
from typing import Any

# Each row is a dict or sqlite3.Row -- anything indexable by column name.
Row = Any


def compute_legal_move_rate(moves: Sequence[Row]) -> float | None:
    if not moves:
        return None
    legal = sum(1 for move in moves if move["is_legal"])
    return legal / len(moves)


def compute_valid_json_rate(dataset_rows: Sequence[Row]) -> float | None:
    if not dataset_rows:
        return None
    valid = 0
    for row in dataset_rows:
        try:
            json.loads(row["payload_json"])
            valid += 1
        except (json.JSONDecodeError, TypeError):
            pass
    return valid / len(dataset_rows)
