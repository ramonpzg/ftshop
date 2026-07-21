import json

import pytest

from chess_adapt.actions.training import push_adapter
from chess_adapt.data.store import PipelinePaths


def test_push_refuses_a_failed_validation_before_network(tmp_path):
    paths = PipelinePaths(tmp_path / "data", tmp_path / "output")
    adapter = paths.adapter("qlora")
    adapter.mkdir(parents=True)
    for filename in ("adapter_config.json", "dataset_manifest.json"):
        (adapter / filename).write_text("{}")
    (adapter / "README.md").write_text("model card")
    (adapter / "run_manifest.json").write_text(
        json.dumps(
            {
                "validation": {
                    "available": True,
                    "sample_count": 8,
                    "legal_move_rate": 0.25,
                }
            }
        )
    )

    with pytest.raises(RuntimeError, match="below the publish threshold"):
        push_adapter(
            paths,
            "qlora",
            "ramonpzg/test",
            private=False,
            min_legal_rate=0.5,
        )
