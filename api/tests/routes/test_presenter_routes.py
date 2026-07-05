from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from euro_chess_studio.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_get_presenter_state_defaults(client: TestClient):
    response = client.get("/presenter")
    assert response.status_code == 200
    assert response.json()["mode"] == "idle"


def test_bring_to_presenter_view(client: TestClient):
    response = client.post("/presenter/bring-to-presenter-view", json={"page_slug": "presentation"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "presenter"
    assert body["active_page_slug"] == "presentation"


def test_bring_to_presenter_view_unknown_page_404s(client: TestClient):
    response = client.post("/presenter/bring-to-presenter-view", json={"page_slug": "nope"})
    assert response.status_code == 404


def test_send_to_workspaces(client: TestClient):
    client.post("/presenter/bring-to-presenter-view", json={"page_slug": "presentation"})
    response = client.post("/presenter/send-to-workspaces")
    assert response.status_code == 200
    assert response.json()["mode"] == "workspaces"


def test_lock_and_unlock(client: TestClient):
    locked = client.post("/presenter/lock").json()
    assert locked["locked"] is True
    unlocked = client.post("/presenter/unlock").json()
    assert unlocked["locked"] is False


def test_reset_page(client: TestClient):
    user = client.post("/users", json={"name": "Ada"}).json()
    workspace = client.post(
        "/workspaces", json={"user_id": user["id"], "page_slug": "chess-machine"}
    ).json()
    client.post(f"/workspaces/{workspace['id']}/moves", json={"uci": "e2e4"})

    response = client.post("/presenter/reset-page", json={"page_slug": "chess-machine"})
    assert response.status_code == 200
    assert response.json()["workspaces_reset"] == 1

    state = client.get(f"/workspaces/{workspace['id']}/state").json()
    assert state["moves"] == []
    assert state["workspace"]["board_fen"] == (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )
