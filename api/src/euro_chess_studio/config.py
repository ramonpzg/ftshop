"""Local app configuration. No secrets, no auth for v0."""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_DB_PATH = REPO_ROOT / "euro_chess_studio.db"


def get_db_path() -> Path:
    override = os.environ.get("CHESS_STUDIO_DB_PATH")
    return Path(override) if override else DEFAULT_DB_PATH


def get_artifacts_dir() -> Path:
    return REPO_ROOT / "artifacts"


def get_data_dir() -> Path:
    return REPO_ROOT / "data"


def get_canvas_dir() -> Path:
    """Where the tldraw document snapshot lives. On disk, not in SQLite,
    so `just reset-db` can wipe workshop state without touching authored
    slides, and so the snapshot can be committed to git."""
    override = os.environ.get("CHESS_STUDIO_CANVAS_DIR")
    return Path(override) if override else get_data_dir() / "canvas"


def get_assets_dir() -> Path:
    """Where uploaded canvas assets (images, video, audio) live."""
    override = os.environ.get("CHESS_STUDIO_ASSETS_DIR")
    return Path(override) if override else get_data_dir() / "assets"
