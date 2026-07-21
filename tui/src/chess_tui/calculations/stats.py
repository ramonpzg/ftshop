"""Pure record aggregation. The personal objective (captures in wins)
is a secondary statistic; it never changes chess scoring."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Record:
    wins: int
    losses: int
    draws: int
    completed: int
    captures_in_wins: int


def compute_record(
    results: list[str | None],
    captures_by_result: list[tuple[str | None, int]],
) -> Record:
    """results: one entry per game (None while unfinished).
    captures_by_result: per game, its result and the participant's
    capture count in it."""
    wins = sum(1 for r in results if r == "1-0")
    losses = sum(1 for r in results if r == "0-1")
    draws = sum(1 for r in results if r == "1/2-1/2")
    captures_in_wins = sum(count for result, count in captures_by_result if result == "1-0")
    return Record(
        wins=wins,
        losses=losses,
        draws=draws,
        completed=wins + losses + draws,
        captures_in_wins=captures_in_wins,
    )
