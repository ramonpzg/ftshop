import json

import pytest

from chess_adapt.actions import training
from chess_adapt.actions.training import pull_adapter, push_adapter
from chess_adapt.data.store import PipelinePaths


def _saved_adapter(paths: PipelinePaths, legal_move_rate: float) -> None:
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
                    "legal_move_rate": legal_move_rate,
                }
            }
        )
    )


def test_push_refuses_a_failed_validation_before_network(tmp_path):
    paths = PipelinePaths(tmp_path / "data", tmp_path / "output")
    _saved_adapter(paths, legal_move_rate=0.25)

    with pytest.raises(RuntimeError, match="below the publish threshold"):
        push_adapter(
            paths,
            "qlora",
            "ramonpzg/test",
            private=False,
            min_legal_rate=0.5,
        )


def test_push_uses_hf_access_token_alias(monkeypatch, tmp_path):
    paths = PipelinePaths(tmp_path / "data", tmp_path / "output")
    _saved_adapter(paths, legal_move_rate=1.0)
    seen = {}

    class FakeApi:
        def create_repo(self, *args, **kwargs):
            seen["create"] = (args, kwargs)

        def upload_folder(self, *args, **kwargs):
            seen["upload"] = (args, kwargs)

    def make_api(*, token=None):
        seen["token"] = token
        return FakeApi()

    monkeypatch.setenv("HF_ACCESS_TOKEN", "hf_test_write_token")
    monkeypatch.setattr(training, "HfApi", make_api)

    url = push_adapter(paths, "qlora", "ramonpzg/test", private=False)

    assert seen["token"] == "hf_test_write_token"
    assert seen["create"][0] == ("ramonpzg/test",)
    assert seen["upload"][1]["folder_path"] == paths.adapter("qlora")
    assert url == "https://huggingface.co/ramonpzg/test"


def test_pull_downloads_and_verifies_public_adapter(monkeypatch, tmp_path):
    paths = PipelinePaths(tmp_path / "data", tmp_path / "output")
    seen = {}

    def fake_download(**kwargs):
        seen.update(kwargs)
        adapter_dir = kwargs["local_dir"]
        for filename in ("adapter_config.json", "adapter_model.safetensors", "README.md"):
            (adapter_dir / filename).write_text("adapter")
        (adapter_dir / "run_manifest.json").write_text(
            json.dumps(
                {
                    "base_model": training.BASE_MODEL,
                    "adapter_type": "qlora",
                }
            )
        )
        return str(adapter_dir)

    monkeypatch.delenv("HF_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(training, "snapshot_download", fake_download)

    adapter_dir = pull_adapter(paths, "qlora", "ramonpzg/test")

    assert adapter_dir == paths.adapter("qlora")
    assert seen["repo_id"] == "ramonpzg/test"
    assert seen["repo_type"] == "model"
    assert seen["token"] is None


def test_pull_refuses_wrong_base_model(monkeypatch, tmp_path):
    paths = PipelinePaths(tmp_path / "data", tmp_path / "output")

    def fake_download(**kwargs):
        adapter_dir = kwargs["local_dir"]
        for filename in ("adapter_config.json", "adapter_model.safetensors", "README.md"):
            (adapter_dir / filename).write_text("adapter")
        (adapter_dir / "run_manifest.json").write_text(
            json.dumps({"base_model": "wrong/base", "adapter_type": "qlora"})
        )
        return str(adapter_dir)

    monkeypatch.setattr(training, "snapshot_download", fake_download)

    with pytest.raises(RuntimeError, match="base model"):
        pull_adapter(paths, "qlora", "ramonpzg/test")
