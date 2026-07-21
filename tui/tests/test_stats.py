"""Record aggregation: unfinished games stay out of the record and
captures only count toward the objective in won games."""

from chess_tui.calculations.stats import compute_record


def test_empty_record():
    record = compute_record([], [])
    assert (record.wins, record.losses, record.draws, record.completed) == (0, 0, 0, 0)
    assert record.captures_in_wins == 0


def test_unfinished_games_are_not_completed():
    record = compute_record(["1-0", None, "0-1", "1/2-1/2", None], [])
    assert record.wins == 1
    assert record.losses == 1
    assert record.draws == 1
    assert record.completed == 3


def test_captures_count_only_in_wins():
    captures = [("1-0", 3), ("0-1", 5), ("1-0", 2), (None, 9), ("1/2-1/2", 4)]
    record = compute_record(["1-0", "0-1", "1-0", None, "1/2-1/2"], captures)
    assert record.captures_in_wins == 5
