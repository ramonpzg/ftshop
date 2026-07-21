"""File access for the reviewed adaptation fixtures under
artifacts/cached/text/. Read-only, no business logic: loaders return
parsed JSON and existence errors, nothing else."""

import json
from typing import Any

from euro_chess_studio.config import get_artifacts_dir


class AdaptationFixtureError(FileNotFoundError):
    pass


def _load(name: str) -> dict[str, Any]:
    path = get_artifacts_dir() / "cached" / "text" / name
    if not path.exists():
        raise AdaptationFixtureError(f"no adaptation fixture at {path}")
    return json.loads(path.read_text())


def load_reference_snapshot_fixture() -> dict[str, Any]:
    return _load("reference_snapshot.json")


def load_eval_suite_fixture() -> dict[str, Any]:
    return _load("eval_suite.json")


def load_training_fixture() -> dict[str, Any]:
    return _load("train_adapter.json")


def load_benchmark_replies_fixture() -> dict[str, Any]:
    return _load("benchmark_replies.json")
