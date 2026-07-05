from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from euro_chess_studio.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_get_evals_returns_seeded_cached_metrics_for_a_modality(client: TestClient):
    response = client.get("/evals", params={"modality": "image"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    assert all(row["source"] == "cached" for row in body)


def test_get_evals_returns_computed_metrics_scoped_to_a_workspace(client: TestClient):
    user = client.post("/users", json={"name": "Ada"}).json()
    workspace = client.post(
        "/workspaces", json={"user_id": user["id"], "page_slug": "chess-machine"}
    ).json()
    client.post(f"/workspaces/{workspace['id']}/moves", json={"uci": "e2e4"})
    client.post("/jobs", json={"job_type": "text.prompt_eval", "workspace_id": workspace["id"]})

    response = client.get("/evals", params={"modality": "text", "workspace_id": workspace["id"]})
    assert response.status_code == 200
    body = response.json()
    assert any(row["metric"] == "legal_move_rate" and row["source"] == "computed" for row in body)
