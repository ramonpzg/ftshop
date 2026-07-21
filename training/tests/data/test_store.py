import json

import pytest

from chess_adapt.data.store import PipelinePaths, pipeline_lock, read_jsonl, write_jsonl


def test_jsonl_round_trip_is_one_object_per_line(tmp_path):
    path = tmp_path / "rows.jsonl"
    rows = [{"a": 1}, {"b": 2}]
    write_jsonl(path, rows)
    assert read_jsonl(path) == rows
    assert [json.loads(line) for line in path.read_text().splitlines()] == rows


def test_jsonl_rejects_non_object_rows(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text("[1, 2]\n")
    with pytest.raises(ValueError, match="not a JSON object"):
        read_jsonl(path)


def test_pipeline_lock_refuses_a_second_writer(tmp_path):
    paths = PipelinePaths(tmp_path / "data", tmp_path / "output")
    with pipeline_lock(paths):
        with pytest.raises(RuntimeError, match="another chess-adapt run"):
            with pipeline_lock(paths):
                pass
