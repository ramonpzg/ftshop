"""Repository tests for adapter identity resolution: the exact-identity
lookup the training replay uses, and newest-first checkpoint
resolution when a label has been retrained."""

from pathlib import Path

from euro_chess_studio.data.adapters_repo import (
    find_adapter,
    get_adapter_by_checkpoint,
    insert_adapter,
)
from euro_chess_studio.data.dataset_snapshots_repo import insert_snapshot
from euro_chess_studio.data.db import get_connection, init_db


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    return conn


def snapshot(conn, label: str, content_hash: str):
    return insert_snapshot(
        conn,
        label=label,
        modality="text",
        origin="frozen",
        schema_version="sft-prompt-completion-v1",
        row_count=1,
        excluded_ineligible_count=0,
        source_game_count=1,
        source_workspace_count=1,
        scenario_raw_count=0,
        scenario_approved_count=0,
        content_hash=content_hash,
        rows=[{"prompt": "p", "completion": "c"}],
        source_row_ids=["r1"],
    )


def adapter(conn, snapshot_row, *, config_hash: str = "hash-config"):
    return insert_adapter(
        conn,
        label="Gemma LoRA",
        modality="text",
        checkpoint="gemma-chess-sft-v1",
        base_model="google/gemma-4-E2B-it-qat-q4_0-unquantized",
        method="lora",
        seed=7,
        output_task="fen to move",
        config_id="text-gemma-lora-v1",
        config_hash=config_hash,
        config={"seed": 7},
        dataset_snapshot_id=snapshot_row["id"],
        dataset_content_hash=snapshot_row["content_hash"],
        runner="replay",
        result_source="cached",
        limitations="adapter only",
    )


def test_find_adapter_matches_the_exact_training_identity(tmp_path: Path):
    conn = make_conn(tmp_path)
    snap = snapshot(conn, "a", "hash-a")
    row = adapter(conn, snap)
    conn.commit()

    assert (
        find_adapter(
            conn,
            modality="text",
            checkpoint="gemma-chess-sft-v1",
            config_hash="hash-config",
            dataset_content_hash="hash-a",
        )["id"]
        == row["id"]
    )
    # A different dataset or config is a different adapter, not a match.
    assert (
        find_adapter(
            conn,
            modality="text",
            checkpoint="gemma-chess-sft-v1",
            config_hash="hash-config",
            dataset_content_hash="hash-b",
        )
        is None
    )
    assert (
        find_adapter(
            conn,
            modality="text",
            checkpoint="gemma-chess-sft-v1",
            config_hash="other-config",
            dataset_content_hash="hash-a",
        )
        is None
    )


def test_checkpoint_resolution_returns_the_newest_adapter(tmp_path: Path):
    conn = make_conn(tmp_path)
    first = adapter(conn, snapshot(conn, "a", "hash-a"))
    # Same checkpoint label retrained against different data later.
    conn.execute(
        "UPDATE adapters SET created_at = '2020-01-01T00:00:00' WHERE id = ?", (first["id"],)
    )
    second = adapter(conn, snapshot(conn, "b", "hash-b"), config_hash="hash-config-2")
    conn.commit()

    resolved = get_adapter_by_checkpoint(conn, "text", "gemma-chess-sft-v1")
    assert resolved["id"] == second["id"]
