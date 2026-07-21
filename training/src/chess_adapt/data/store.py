"""Atomic local storage for resumable dataset and training artifacts."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PipelinePaths:
    data_dir: Path
    output_dir: Path

    @property
    def games(self) -> Path:
        return self.data_dir / "games.jsonl"

    @property
    def enrichments(self) -> Path:
        return self.data_dir / "enrichments.jsonl"

    @property
    def manifest(self) -> Path:
        return self.data_dir / "manifest.json"

    def split(self, name: str) -> Path:
        return self.data_dir / f"sft_{name}.jsonl"

    def adapter(self, method: str) -> Path:
        return self.output_dir / method / "adapter"

    def work(self, method: str) -> Path:
        return self.output_dir / method / "work"

    @property
    def lock(self) -> Path:
        return self.data_dir / ".pipeline.lock"


@contextmanager
def pipeline_lock(paths: PipelinePaths) -> Iterator[None]:
    """One local pipeline per output set. The OS releases this lock on exit."""
    import fcntl

    paths.data_dir.mkdir(parents=True, exist_ok=True)
    with paths.lock.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another chess-adapt run holds {paths.lock}") from exc
        handle.write(f"pid={os.getpid()}\n")
        handle.flush()
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            rows.append(value)
    return rows


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    body = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    _atomic_write(path, body)


def write_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _atomic_write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
