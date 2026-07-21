"""Pinned, bounded access to the official Lichess Hugging Face dataset."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

DATASET_ID = "Lichess/standard-chess-games"
DATASET_REVISION = "de4e636eddf568a9394cc01fb0b9e1da04a6babf"
SOURCE_FILE = "data/year=2013/month=01/train-00000-of-00001.parquet"
SOURCE_LICENSE = "CC0-1.0"

SOURCE_COLUMNS = [
    "Event",
    "Site",
    "Result",
    "WhiteElo",
    "BlackElo",
    "UTCDate",
    "UTCTime",
    "ECO",
    "Opening",
    "Termination",
    "TimeControl",
    "movetext",
]


@dataclass(frozen=True)
class LichessSource:
    dataset_id: str
    revision: str
    filename: str
    license: str
    local_path: Path
    row_count: int


def open_source(*, offline: bool = False) -> tuple[LichessSource, Iterator[dict[str, Any]]]:
    """Resolve one 37 MB partition and stream it in small Arrow batches."""
    local_path = Path(
        hf_hub_download(
            repo_id=DATASET_ID,
            repo_type="dataset",
            revision=DATASET_REVISION,
            filename=SOURCE_FILE,
            local_files_only=offline,
        )
    )
    parquet = pq.ParquetFile(local_path)
    source = LichessSource(
        dataset_id=DATASET_ID,
        revision=DATASET_REVISION,
        filename=SOURCE_FILE,
        license=SOURCE_LICENSE,
        local_path=local_path,
        row_count=parquet.metadata.num_rows,
    )

    def rows() -> Iterator[dict[str, Any]]:
        for batch in parquet.iter_batches(batch_size=1_024, columns=SOURCE_COLUMNS):
            yield from batch.to_pylist()

    return source, rows()
