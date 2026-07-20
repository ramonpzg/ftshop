"""Action: export the room's game data as a trainable JSONL file."""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from euro_chess_studio.calculations.export import (
    build_scenario_export_rows,
    build_sft_rows,
    is_training_eligible,
    to_jsonl,
)
from euro_chess_studio.config import get_data_dir
from euro_chess_studio.data.dataset_rows_repo import (
    list_all_dataset_rows_with_move_provenance,
    list_dataset_rows_by_shape_with_move_provenance,
)
from euro_chess_studio.data.scenario_repo import list_scenarios

EXPORT_FILE_NAME = "chess_sft.jsonl"
FULL_EXPORT_FILE_NAME = "chess_all_shapes.jsonl"
SCENARIO_EXPORT_FILE_NAME = "chess_scenarios.jsonl"


def get_text_export_path() -> Path:
    return get_data_dir() / "processed" / "text" / EXPORT_FILE_NAME


def get_full_export_path() -> Path:
    return get_data_dir() / "processed" / "text" / FULL_EXPORT_FILE_NAME


def get_scenario_export_path() -> Path:
    return get_data_dir() / "processed" / "text" / SCENARIO_EXPORT_FILE_NAME


@dataclass(frozen=True)
class ExportResult:
    file_name: str
    row_count: int
    path: str


def export_text_dataset(conn: sqlite3.Connection) -> ExportResult:
    """Writes every eligible workspace's fen+legal-moves rows as
    prompt/completion JSONL. This file is what the training snippets and
    the notebooks load, so playing a game on stage directly becomes
    training data. Fallback moves (the deterministic placeholder played
    when the model produced nothing usable) are not eligible: they would
    teach an arbitrary lexicographic choice as if it were a real answer.
    """
    stored = list_dataset_rows_by_shape_with_move_provenance(conn, "fen_legal_moves_to_move")
    payloads = [{**json.loads(row["payload_json"]), "actor": row["move_actor"]} for row in stored]
    rows = build_sft_rows(payloads)

    path = get_text_export_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    tmp.write_text(to_jsonl(rows))
    tmp.replace(path)

    return ExportResult(file_name=EXPORT_FILE_NAME, row_count=len(rows), path=str(path))


def export_full_dataset(conn: sqlite3.Connection) -> ExportResult:
    """The instructor's archive: every dataset row from every workspace,
    all six shapes, one JSON object per line with the shape, the move
    that produced it (id, game, actor, model), and an explicit
    training_eligible flag alongside the payload. This is a complete
    audit trail, not a ready-to-train file by itself: a training
    pipeline reading it must still filter on training_eligible the way
    chess_sft.jsonl does automatically, since fallback-actor rows are
    included here for completeness but are not legitimate targets."""
    rows = [
        {
            "shape": row["shape"],
            "workspace_id": row["workspace_id"],
            "move_id": row["move_id"],
            "game_id": row["move_game_id"],
            "actor": row["move_actor"],
            "model": row["move_model"],
            "training_eligible": is_training_eligible(row["move_actor"]),
            "created_at": row["created_at"],
            **json.loads(row["payload_json"]),
        }
        for row in list_all_dataset_rows_with_move_provenance(conn)
    ]

    path = get_full_export_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    tmp.write_text(to_jsonl(rows))
    tmp.replace(path)

    return ExportResult(file_name=FULL_EXPORT_FILE_NAME, row_count=len(rows), path=str(path))


def export_scenarios(conn: sqlite3.Connection) -> ExportResult:
    """The room's scenario mappings with full provenance: the raw model
    suggestion and, separately, whatever a participant approved."""
    rows = build_scenario_export_rows([dict(row) for row in list_scenarios(conn)])

    path = get_scenario_export_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    tmp.write_text(to_jsonl(rows))
    tmp.replace(path)

    return ExportResult(file_name=SCENARIO_EXPORT_FILE_NAME, row_count=len(rows), path=str(path))
