from pathlib import Path

import pytest

from euro_chess_studio.data.assets_store import (
    asset_path,
    delete_asset,
    is_safe_name,
    list_asset_names,
    save_asset,
)


@pytest.mark.parametrize(
    "name",
    ["board.png", "asset-abc123.jpeg", "clip_01.mp4", "a.b.c.webm", "X9.svg"],
)
def test_safe_names_accepted(name: str):
    assert is_safe_name(name)


@pytest.mark.parametrize(
    "name",
    ["", "../escape.png", "..", ".hidden", "/etc/passwd", "a/b.png", "a\\b.png", "-dash.png"],
)
def test_unsafe_names_rejected(name: str):
    assert not is_safe_name(name)


def test_save_then_read_roundtrip(tmp_path: Path):
    save_asset(tmp_path, "piece.png", b"\x89PNG fake bytes")
    path = asset_path(tmp_path, "piece.png")
    assert path is not None
    assert path.read_bytes() == b"\x89PNG fake bytes"


def test_save_rejects_unsafe_name(tmp_path: Path):
    with pytest.raises(ValueError):
        save_asset(tmp_path, "../escape.png", b"data")


def test_asset_path_returns_none_for_missing_or_unsafe(tmp_path: Path):
    assert asset_path(tmp_path, "missing.png") is None
    assert asset_path(tmp_path, "../escape.png") is None


def test_list_asset_names_sorted_and_files_only(tmp_path: Path):
    save_asset(tmp_path, "b.png", b"b")
    save_asset(tmp_path, "a.png", b"a")
    (tmp_path / "subdir").mkdir()
    assert list_asset_names(tmp_path) == ["a.png", "b.png"]


def test_list_asset_names_empty_when_dir_missing(tmp_path: Path):
    assert list_asset_names(tmp_path / "nope") == []


def test_delete_asset(tmp_path: Path):
    save_asset(tmp_path, "gone.png", b"data")
    assert delete_asset(tmp_path, "gone.png") is True
    assert asset_path(tmp_path, "gone.png") is None
    assert delete_asset(tmp_path, "gone.png") is False
