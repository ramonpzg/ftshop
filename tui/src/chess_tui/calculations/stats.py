"""Pure record aggregation, aware that the participant's color is
assigned per game. The personal objective (captures in wins) is a
secondary statistic; it never changes chess scoring."""

from dataclasses import dataclass

_WIN_BY_COLOR = {"white": "1-0", "black": "0-1"}


@dataclass(frozen=True)
class Record:
    wins: int
    losses: int
    draws: int
    completed: int
    captures_in_wins: int


def participant_won(result: str | None, participant_color: str) -> bool:
    return result is not None and result == _WIN_BY_COLOR.get(participant_color)


def participant_lost(result: str | None, participant_color: str) -> bool:
    if result not in ("1-0", "0-1"):
        return False
    return not participant_won(result, participant_color)


def compute_record(
    results: list[tuple[str | None, str]],
    captures_by_game: list[tuple[str | None, str, int]],
) -> Record:
    """results: (result, participant_color) per game; result is None
    while unfinished. captures_by_game adds the participant's capture
    count per game."""
    wins = sum(1 for result, color in results if participant_won(result, color))
    losses = sum(1 for result, color in results if participant_lost(result, color))
    draws = sum(1 for result, _ in results if result == "1/2-1/2")
    captures_in_wins = sum(
        count for result, color, count in captures_by_game if participant_won(result, color)
    )
    return Record(
        wins=wins,
        losses=losses,
        draws=draws,
        completed=wins + losses + draws,
        captures_in_wins=captures_in_wins,
    )
