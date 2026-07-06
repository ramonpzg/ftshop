"""File storage for generated job outputs (images, video, audio).

No business logic here. Same safe-name discipline as the canvas asset
store: a name can never escape the generated directory.
"""

from pathlib import Path

from euro_chess_studio.data.assets_store import is_safe_name


def save_generated(generated_dir: Path, name: str, content: bytes) -> Path:
    if not is_safe_name(name):
        raise ValueError(f"unsafe generated file name: {name!r}")
    generated_dir.mkdir(parents=True, exist_ok=True)
    path = generated_dir / name
    tmp = generated_dir / (name + ".tmp")
    tmp.write_bytes(content)
    tmp.replace(path)
    return path


def generated_path(generated_dir: Path, name: str) -> Path | None:
    if not is_safe_name(name):
        return None
    path = generated_dir / name
    return path if path.is_file() else None
