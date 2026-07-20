from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from euro_chess_studio.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_get_job_types_lists_all_job_types(client: TestClient):
    response = client.get("/jobs/types")
    assert response.status_code == 200
    assert len(response.json()) == 14


def test_post_job_runs_a_local_job(client: TestClient):
    response = client.post(
        "/jobs",
        json={"job_type": "audio.make_spectrogram", "params": {"tags": ["capture"]}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["artifact"]["modality"] == "audio"
    assert body["artifact"]["cached"] is False


def test_post_job_runs_a_replay_job(client: TestClient):
    response = client.post("/jobs", json={"job_type": "image.show_dataset", "params": {}})
    assert response.status_code == 200
    assert response.json()["artifact"]["cached"] is True


def test_post_job_with_unknown_job_type_is_unprocessable(client: TestClient):
    response = client.post("/jobs", json={"job_type": "not.a.job", "params": {}})
    assert response.status_code == 422


def test_post_job_text_eval_against_a_real_workspace(client: TestClient):
    user = client.post("/users", json={"name": "Ada"}).json()
    workspace = client.post(
        "/workspaces", json={"user_id": user["id"], "page_slug": "chess-machine"}
    ).json()
    client.post(f"/workspaces/{workspace['id']}/moves", json={"uci": "e2e4"})

    response = client.post(
        "/jobs", json={"job_type": "text.prompt_eval", "workspace_id": workspace["id"]}
    )
    assert response.status_code == 200
    metrics = {
        entry["metric"]: entry for entry in response.json()["artifact"]["payload"]["metrics"]
    }
    assert metrics["legal_move_rate"]["value"] == 1.0
    assert metrics["legal_move_rate"]["numerator"] == 1
    assert metrics["legal_move_rate"]["denominator"] == 1
    # No model attempts yet: the model metrics are explicitly
    # unavailable, not zero and not perfect.
    assert metrics["model_legal_move_rate"]["available"] is False
