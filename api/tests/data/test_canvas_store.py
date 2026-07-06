import json
from pathlib import Path

from euro_chess_studio.data.canvas_store import (
    BACKUP_NAME,
    SNAPSHOT_NAME,
    read_snapshot,
    write_snapshot,
)


def test_read_snapshot_returns_none_when_nothing_saved(tmp_path: Path):
    assert read_snapshot(tmp_path / "canvas") is None


def test_write_then_read_roundtrip(tmp_path: Path):
    canvas_dir = tmp_path / "canvas"
    snapshot = {"store": {"shape:a": {"x": 1}}, "schema": {"schemaVersion": 2}}
    write_snapshot(canvas_dir, snapshot)
    assert read_snapshot(canvas_dir) == snapshot


def test_second_write_keeps_previous_as_backup(tmp_path: Path):
    canvas_dir = tmp_path / "canvas"
    write_snapshot(canvas_dir, {"version": 1})
    write_snapshot(canvas_dir, {"version": 2})
    assert read_snapshot(canvas_dir) == {"version": 2}
    backup = json.loads((canvas_dir / BACKUP_NAME).read_text())
    assert backup == {"version": 1}


def test_corrupted_snapshot_falls_back_to_backup(tmp_path: Path):
    canvas_dir = tmp_path / "canvas"
    write_snapshot(canvas_dir, {"version": 1})
    write_snapshot(canvas_dir, {"version": 2})
    (canvas_dir / SNAPSHOT_NAME).write_text("{not json")
    assert read_snapshot(canvas_dir) == {"version": 1}


def test_corrupted_snapshot_without_backup_returns_none(tmp_path: Path):
    canvas_dir = tmp_path / "canvas"
    canvas_dir.mkdir()
    (canvas_dir / SNAPSHOT_NAME).write_text("{not json")
    assert read_snapshot(canvas_dir) is None


def test_non_object_snapshot_file_is_treated_as_unreadable(tmp_path: Path):
    canvas_dir = tmp_path / "canvas"
    canvas_dir.mkdir()
    (canvas_dir / SNAPSHOT_NAME).write_text(json.dumps([1, 2, 3]))
    assert read_snapshot(canvas_dir) is None
