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
