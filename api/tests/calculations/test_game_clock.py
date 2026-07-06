from datetime import UTC, datetime, timedelta

from euro_chess_studio.calculations.game_clock import (
    is_expired,
    is_valid_time_limit,
    remaining_seconds,
    summarize_results,
)


def test_time_limits_run_from_one_minute_to_thirty():
    assert not is_valid_time_limit(59)
    assert is_valid_time_limit(60)
    assert is_valid_time_limit(300)
    assert is_valid_time_limit(1800)
    assert not is_valid_time_limit(1801)


def test_remaining_seconds_counts_down_and_stops_at_zero():
    now = datetime.now(UTC)
    started = (now - timedelta(seconds=100)).isoformat()
    assert remaining_seconds(started, 300, now) == 200.0
    assert remaining_seconds(started, 60, now) == 0.0


def test_is_expired_flips_exactly_when_the_clock_runs_out():
    now = datetime.now(UTC)
    fresh = (now - timedelta(seconds=299)).isoformat()
    stale = (now - timedelta(seconds=301)).isoformat()
    assert not is_expired(fresh, 300, now)
    assert is_expired(stale, 300, now)


def test_summarize_results_counts_every_kind_of_loss_as_a_loss():
    record = summarize_results(["loss_resign", "loss_timeout", "loss", "win", "draw"])
    assert record == {"wins": 1, "losses": 3, "draws": 1}


def test_summarize_results_with_no_games_is_all_zero():
    assert summarize_results([]) == {"wins": 0, "losses": 0, "draws": 0}
