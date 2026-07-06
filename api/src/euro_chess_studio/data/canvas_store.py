"""File-backed storage for the tldraw canvas document snapshot.

No business logic here. The snapshot is opaque JSON produced by the
frontend; the backend never inspects it. Writes are atomic (temp file
plus rename) and keep a one-step rolling backup so a crash mid-write or
a corrupted file never costs the presenter their authored slides.
"""

import json
import shutil
from pathlib import Path
from typing import Any

SNAPSHOT_NAME = "snapshot.json"
BACKUP_NAME = "snapshot.prev.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return loaded if isinstance(loaded, dict) else None


def read_snapshot(canvas_dir: Path) -> dict[str, Any] | None:
    """Current snapshot, falling back to the backup if the main file is
    missing or unreadable. None when neither exists."""
    current = _read_json(canvas_dir / SNAPSHOT_NAME)
    if current is not None:
        return current
    return _read_json(canvas_dir / BACKUP_NAME)


def write_snapshot(canvas_dir: Path, snapshot: dict[str, Any]) -> None:
    canvas_dir.mkdir(parents=True, exist_ok=True)
    path = canvas_dir / SNAPSHOT_NAME
    tmp = canvas_dir / (SNAPSHOT_NAME + ".tmp")
    tmp.write_text(json.dumps(snapshot))
    if path.exists():
        shutil.copy2(path, canvas_dir / BACKUP_NAME)
    tmp.replace(path)
