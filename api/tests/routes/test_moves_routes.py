from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from euro_chess_studio.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    # Game starts model the full-room configuration: a local endpoint
    # serves the default opponent, so the room policy lets them through.
    monkeypatch.setenv("OPPONENT_ENDPOINT_IS_LOCAL", "1")
    with TestClient(app) as test_client:
        yield test_client


def make_workspace(client: TestClient) -> str:
    user = client.post("/users", json={"name": "Ada"}).json()
    workspace = client.post(
        "/workspaces", json={"user_id": user["id"], "page_slug": "chess-machine"}
    ).json()
    return workspace["id"]


def test_legal_move_updates_board_and_returns_dataset_rows(client: TestClient):
    workspace_id = make_workspace(client)
    response = client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "e2e4"})
    assert response.status_code == 200
    body = response.json()
    assert body["move"]["is_legal"] is True
    assert body["move"]["san"] == "e4"
    assert len(body["dataset_rows"]) == 6


def test_illegal_move_is_rejected_but_recorded(client: TestClient):
    workspace_id = make_workspace(client)
    response = client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "e2e5"})
    assert response.status_code == 200
    body = response.json()
    assert body["move"]["is_legal"] is False
    assert body["dataset_rows"] == []


def test_move_on_unknown_workspace_returns_404(client: TestClient):
    response = client.post("/workspaces/does-not-exist/moves", json={"uci": "e2e4"})
    assert response.status_code == 404


def test_moving_the_models_color_in_an_active_game_is_rejected(client: TestClient):
    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/game/start", json={})
    client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "e2e4"})

    response = client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "e7e5"})

    assert response.status_code == 409
    body = response.json()["detail"]
    assert body["code"] == "not_your_turn"
    assert "model's turn" in body["message"]


def test_workspace_state_reflects_moves_and_dataset(client: TestClient):
    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "e2e4"})

    response = client.get(f"/workspaces/{workspace_id}/state")
    assert response.status_code == 200
    body = response.json()
    assert body["workspace"]["board_fen"] != (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )
    assert len(body["moves"]) == 1
    assert len(body["dataset_rows"]) == 6
