"""Configuration: defaults, environment, CLI flags. The API key is
never persisted, never displayed, and excluded from repr; the default
local server does not need a real credential."""

import os
from dataclasses import dataclass, field
from pathlib import Path

# 9017 because half the world already squats on 8080, Ramon's phone
# included.
DEFAULT_BASE_URL = "http://127.0.0.1:9017/v1"
DEFAULT_MODEL = "gemma-4-2b-local"
DEFAULT_API_KEY = "local"
# Phone inference budget: a mid-game prompt is a few hundred tokens and
# Gemma 4 E2B Q4_0 generates a bounded JSON object, but a cold prompt
# cache on a phone CPU can take a while. docs/phone-tui.md documents
# the measured shape of this.
DEFAULT_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class Config:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    api_key: str = field(default=DEFAULT_API_KEY, repr=False)
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    db_path: Path = field(default_factory=lambda: default_db_path(os.environ))
    no_color: bool = False
    player_name: str | None = None  # None means ask once and persist


def default_db_path(env: dict | os._Environ) -> Path:
    """XDG data directory, which exists on Termux too. Tests point
    CHESS_TUI_DB somewhere temporary instead."""
    override = env.get("CHESS_TUI_DB")
    if override:
        return Path(override)
    xdg = env.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "chess-tui" / "games.db"


def normalize_base_url(url: str) -> str:
    """One place strips the trailing slash so every joiner can assume
    it is absent."""
    return url.strip().rstrip("/")


def load_config(
    env: dict | os._Environ,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    timeout: float | None = None,
    db: str | None = None,
    no_color: bool = False,
    name: str | None = None,
) -> Config:
    """Flags beat environment beats defaults."""
    resolved_timeout = timeout
    if resolved_timeout is None:
        raw = env.get("CHESS_TUI_TIMEOUT")
        resolved_timeout = float(raw) if raw else DEFAULT_TIMEOUT_SECONDS
    return Config(
        base_url=normalize_base_url(base_url or env.get("CHESS_TUI_BASE_URL") or DEFAULT_BASE_URL),
        model=model or env.get("CHESS_TUI_MODEL") or DEFAULT_MODEL,
        api_key=api_key or env.get("CHESS_TUI_API_KEY") or DEFAULT_API_KEY,
        timeout_seconds=resolved_timeout,
        db_path=Path(db) if db else default_db_path(env),
        no_color=no_color or bool(env.get("NO_COLOR")),
        player_name=name or env.get("CHESS_TUI_NAME") or None,
    )
