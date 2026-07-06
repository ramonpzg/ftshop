"""Pure clock and record arithmetic for timed games. No I/O here.

A game has one clock for the whole match. When it runs out, that is a
loss. Starting over is also a loss. The Duolingo rule: quitting costs
you, which is exactly why people stop quitting.
"""

from collections.abc import Iterable
from datetime import datetime

DEFAULT_TIME_LIMIT_SECONDS = 300
MIN_TIME_LIMIT_SECONDS = 60
MAX_TIME_LIMIT_SECONDS = 1800

# Every way a game can end. "loss_resign" is the start-over button,
# "loss_timeout" is the clock, plain "win"/"loss" are checkmates
# (yours / the model's), "draw" is a stalemate.
LOSS_RESULTS = ("loss_resign", "loss_timeout", "loss")
WIN_RESULTS = ("win",)
DRAW_RESULTS = ("draw",)


def is_valid_time_limit(seconds: int) -> bool:
    return MIN_TIME_LIMIT_SECONDS <= seconds <= MAX_TIME_LIMIT_SECONDS


def remaining_seconds(started_at: str, time_limit_seconds: int, now: datetime) -> float:
    """Seconds left on the clock, never below zero."""
    elapsed = (now - datetime.fromisoformat(started_at)).total_seconds()
    return max(0.0, time_limit_seconds - elapsed)


def is_expired(started_at: str, time_limit_seconds: int, now: datetime) -> bool:
    return remaining_seconds(started_at, time_limit_seconds, now) <= 0.0


def summarize_results(results: Iterable[str]) -> dict:
    """Collapses finished-game results into a W/L/D record."""
    record = {"wins": 0, "losses": 0, "draws": 0}
    for result in results:
        if result in WIN_RESULTS:
            record["wins"] += 1
        elif result in LOSS_RESULTS:
            record["losses"] += 1
        elif result in DRAW_RESULTS:
            record["draws"] += 1
    return record
