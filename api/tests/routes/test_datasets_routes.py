import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from euro_chess_studio.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("CHESS_STUDIO_DATA_DIR", str(tmp_path / "data"))
    with TestClient(app) as test_client:
        yield test_client


def test_export_before_any_moves_writes_an_empty_file(client: TestClient):
    response = client.post("/datasets/text/export")
    assert response.status_code == 200
    assert response.json()["row_count"] == 0


def test_get_export_is_404_before_first_export(client: TestClient):
    assert client.get("/datasets/text/chess_sft.jsonl").status_code == 404


def test_played_moves_export_as_trainable_jsonl(client: TestClient):
    user = client.post("/users", json={"name": "Ada"}).json()
    workspace = client.post(
        "/workspaces", json={"user_id": user["id"], "page_slug": "chess-machine"}
    ).json()
    client.post(f"/workspaces/{workspace['id']}/moves", json={"uci": "e2e4"})
    client.post(f"/workspaces/{workspace['id']}/moves", json={"uci": "e7e5"})

    response = client.post("/datasets/text/export")
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 2
    assert body["url"] == "/datasets/text/chess_sft.jsonl"

    download = client.get("/datasets/text/chess_sft.jsonl")
    assert download.status_code == 200
    lines = download.text.strip().split("\n")
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert "Position (FEN)" in first["prompt"]
    assert json.loads(first["completion"])["move"] == "e2e4"
