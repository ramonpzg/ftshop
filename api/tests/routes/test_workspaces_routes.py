from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from euro_chess_studio.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_create_user_and_workspace(client: TestClient):
    user_response = client.post("/users", json={"name": "Ada"})
    assert user_response.status_code == 201
    user = user_response.json()

    ws_response = client.post(
        "/workspaces", json={"user_id": user["id"], "page_slug": "chess-machine"}
    )
    assert ws_response.status_code == 201
    workspace = ws_response.json()
    assert workspace["user_id"] == user["id"]
    assert workspace["position_index"] == 0


def test_create_workspace_for_unknown_page_returns_404(client: TestClient):
    user = client.post("/users", json={"name": "Ada"}).json()
    response = client.post("/workspaces", json={"user_id": user["id"], "page_slug": "nope"})
    assert response.status_code == 404


def test_create_user_rejects_blank_name(client: TestClient):
    response = client.post("/users", json={"name": "   "})
    assert response.status_code == 422


def test_list_workspaces_includes_details(client: TestClient):
    user = client.post("/users", json={"name": "Ada"}).json()
    client.post("/workspaces", json={"user_id": user["id"], "page_slug": "chess-machine"})

    response = client.get("/workspaces")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["user_name"] == "Ada"
    assert body[0]["page_slug"] == "chess-machine"
