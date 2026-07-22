"""Record aggregation with per-game colors: a 0-1 is a win when the
participant had Black, unfinished games stay out, and captures only
count toward the objective in won games."""

from chess_tui.calculations.stats import compute_record, participant_lost, participant_won


def test_win_loss_depends_on_color():
    assert participant_won("1-0", "white")
    assert participant_won("0-1", "black")
    assert not participant_won("1-0", "black")
    assert participant_lost("1-0", "black")
    assert participant_lost("0-1", "white")
    assert not participant_lost("1/2-1/2", "white")
    assert not participant_won(None, "white")


def test_empty_record():
    record = compute_record([], [])
    assert (record.wins, record.losses, record.draws, record.completed) == (0, 0, 0, 0)
    assert record.captures_in_wins == 0


def test_record_counts_by_color():
    results = [
        ("1-0", "white"),  # win
        ("0-1", "black"),  # win
        ("0-1", "white"),  # loss
        ("1/2-1/2", "black"),  # draw
        (None, "white"),  # unfinished
    ]
    record = compute_record(results, [])
    assert record.wins == 2
    assert record.losses == 1
    assert record.draws == 1
    assert record.completed == 4


def test_captures_count_only_in_wins():
    captures = [
        ("1-0", "white", 3),  # win as white
        ("0-1", "black", 4),  # win as black
        ("0-1", "white", 5),  # loss
        (None, "white", 9),  # unfinished
    ]
    results = [("1-0", "white"), ("0-1", "black"), ("0-1", "white"), (None, "white")]
    record = compute_record(results, captures)
    assert record.captures_in_wins == 7
