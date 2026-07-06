"""Action: export the room's game data as a trainable JSONL file."""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from euro_chess_studio.calculations.export import build_sft_rows, to_jsonl
from euro_chess_studio.config import get_data_dir
from euro_chess_studio.data.dataset_rows_repo import list_dataset_rows_by_shape

EXPORT_FILE_NAME = "chess_sft.jsonl"


def get_text_export_path() -> Path:
    return get_data_dir() / "processed" / "text" / EXPORT_FILE_NAME


@dataclass(frozen=True)
class ExportResult:
    file_name: str
    row_count: int
    path: str


def export_text_dataset(conn: sqlite3.Connection) -> ExportResult:
    """Writes every workspace's fen+legal-moves rows as prompt/completion
    JSONL. This file is what the training snippets and the notebooks
    load, so playing a game on stage directly becomes training data."""
    stored = list_dataset_rows_by_shape(conn, "fen_legal_moves_to_move")
    payloads = [json.loads(row["payload_json"]) for row in stored]
    rows = build_sft_rows(payloads)

    path = get_text_export_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    tmp.write_text(to_jsonl(rows))
    tmp.replace(path)

    return ExportResult(file_name=EXPORT_FILE_NAME, row_count=len(rows), path=str(path))
