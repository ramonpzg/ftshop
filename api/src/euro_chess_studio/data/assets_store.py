"""File-backed storage for uploaded canvas assets (images, video, audio).

No business logic here. Assets are stored under their client-provided
name, which must pass is_safe_name so a name can never escape the
assets directory.
"""

import re
from pathlib import Path

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def is_safe_name(name: str) -> bool:
    return bool(_SAFE_NAME.match(name)) and ".." not in name


def save_asset(assets_dir: Path, name: str, content: bytes) -> Path:
    if not is_safe_name(name):
        raise ValueError(f"unsafe asset name: {name!r}")
    assets_dir.mkdir(parents=True, exist_ok=True)
    path = assets_dir / name
    tmp = assets_dir / (name + ".tmp")
    tmp.write_bytes(content)
    tmp.replace(path)
    return path


def asset_path(assets_dir: Path, name: str) -> Path | None:
    if not is_safe_name(name):
        return None
    path = assets_dir / name
    return path if path.is_file() else None


def list_asset_names(assets_dir: Path) -> list[str]:
    if not assets_dir.is_dir():
        return []
    return sorted(p.name for p in assets_dir.iterdir() if p.is_file() and is_safe_name(p.name))


def delete_asset(assets_dir: Path, name: str) -> bool:
    path = asset_path(assets_dir, name)
    if path is None:
        return False
    path.unlink()
    return True
