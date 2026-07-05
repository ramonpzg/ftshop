from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from euro_chess_studio.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_get_artifacts_filters_by_modality(client: TestClient):
    client.post("/jobs", json={"job_type": "audio.make_spectrogram", "params": {}})
    client.post("/jobs", json={"job_type": "video.sample_frames", "params": {}})

    response = client.get("/artifacts", params={"modality": "audio"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["modality"] == "audio"


def test_get_artifacts_filters_by_workspace(client: TestClient):
    user = client.post("/users", json={"name": "Ada"}).json()
    workspace = client.post(
        "/workspaces", json={"user_id": user["id"], "page_slug": "chess-machine"}
    ).json()
    client.post("/jobs", json={"job_type": "text.reward_eval", "workspace_id": workspace["id"]})
    client.post("/jobs", json={"job_type": "audio.make_spectrogram", "params": {}})

    response = client.get("/artifacts", params={"workspace_id": workspace["id"]})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["modality"] == "text"
