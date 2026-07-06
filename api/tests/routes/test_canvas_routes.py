from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from euro_chess_studio.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("CHESS_STUDIO_CANVAS_DIR", str(tmp_path / "canvas"))
    monkeypatch.setenv("CHESS_STUDIO_ASSETS_DIR", str(tmp_path / "assets"))
    with TestClient(app) as test_client:
        yield test_client


def test_get_canvas_is_null_before_first_save(client: TestClient):
    response = client.get("/canvas")
    assert response.status_code == 200
    assert response.json() == {"snapshot": None}


def test_put_then_get_canvas_roundtrip(client: TestClient):
    snapshot = {"store": {"shape:x": {"type": "note"}}, "schema": {"schemaVersion": 2}}
    response = client.put("/canvas", json={"snapshot": snapshot})
    assert response.status_code == 200
    assert response.json() == {"saved": True}

    response = client.get("/canvas")
    assert response.json() == {"snapshot": snapshot}


def test_put_canvas_survives_backend_restart(client: TestClient, tmp_path: Path):
    snapshot = {"store": {}, "schema": {"v": 1}}
    client.put("/canvas", json={"snapshot": snapshot})
    # A new TestClient context is a fresh app lifespan: same as stopping
    # and restarting uvicorn.
    with TestClient(app) as second_boot:
        assert second_boot.get("/canvas").json() == {"snapshot": snapshot}


def test_upload_then_fetch_asset(client: TestClient):
    response = client.post(
        "/canvas/assets",
        files={"file": ("board.png", b"\x89PNG fake bytes", "image/png")},
    )
    assert response.status_code == 200
    assert response.json() == {"name": "board.png"}

    response = client.get("/canvas/assets/board.png")
    assert response.status_code == 200
    assert response.content == b"\x89PNG fake bytes"
    assert response.headers["content-type"] == "image/png"


def test_upload_rejects_unsafe_name(client: TestClient):
    response = client.post(
        "/canvas/assets",
        files={"file": ("../escape.png", b"data", "image/png")},
    )
    assert response.status_code == 400


def test_fetch_missing_asset_is_404(client: TestClient):
    assert client.get("/canvas/assets/missing.png").status_code == 404


def test_list_assets(client: TestClient):
    client.post("/canvas/assets", files={"file": ("b.mp4", b"b", "video/mp4")})
    client.post("/canvas/assets", files={"file": ("a.png", b"a", "image/png")})
    response = client.get("/canvas/assets")
    assert response.json() == {"names": ["a.png", "b.mp4"]}


def test_delete_asset(client: TestClient):
    client.post("/canvas/assets", files={"file": ("gone.png", b"data", "image/png")})
    assert client.delete("/canvas/assets/gone.png").json() == {"deleted": True}
    assert client.get("/canvas/assets/gone.png").status_code == 404
    assert client.delete("/canvas/assets/gone.png").json() == {"deleted": False}
