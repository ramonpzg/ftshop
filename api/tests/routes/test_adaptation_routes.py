"""Route tests for the adaptation chain: state assembly, snapshot
freezing, the jobs-route error mapping for adaptation failures, and the
cached media file route."""

import pytest
from fastapi.testclient import TestClient

from euro_chess_studio.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(app) as c:
        yield c


def test_state_is_seeded_at_startup(client: TestClient):
    state = client.get("/adaptation/state").json()
    assert len(state["snapshots"]) == 1
    assert state["snapshots"][0]["origin"] == "seeded"
    assert state["snapshots"][0]["content_hash"]
    assert "rows_json" not in state["snapshots"][0]
    assert state["snapshots"][0]["row_preview"]
    assert len(state["suites"]) == 1
    assert state["suites"][0]["example_count"] == 12
    assert state["configs"][0]["config_id"] == "text-gemma-lora-v1"
    assert state["comparison"] is None
    assert state["live_benchmark"]["available"] is False


def test_freeze_snapshot_returns_409_for_an_empty_room(client: TestClient):
    response = client.post("/adaptation/snapshots", json={})
    assert response.status_code == 409
    assert "no training-eligible rows" in response.json()["detail"]


def test_full_chain_through_the_routes(client: TestClient):
    state = client.get("/adaptation/state").json()
    snapshot = state["snapshots"][0]
    suite = state["suites"][0]

    train = client.post(
        "/jobs",
        json={
            "job_type": "text.train_adapter",
            "params": {
                "dataset_snapshot_id": snapshot["id"],
                "config_id": "text-gemma-lora-v1",
            },
        },
    )
    assert train.status_code == 200
    assert train.json()["artifact"]["cached"] is True
    assert train.json()["artifact"]["payload"]["result_source"] == "cached"

    for checkpoint in ("base", "gemma-chess-sft-v1"):
        run = client.post(
            "/jobs",
            json={
                "job_type": "text.benchmark_eval",
                "params": {"suite_id": suite["id"], "checkpoint": checkpoint},
            },
        )
        assert run.status_code == 200
        payload = run.json()["artifact"]["payload"]
        assert payload["source"] == "replayed"
        assert payload["position_set_id"] == suite["position_set_id"]

    state = client.get("/adaptation/state").json()
    comparison = state["comparison"]
    assert comparison["comparable"] is True
    metrics = {m["metric"]: m for m in comparison["metrics"]}
    assert metrics["model_legal_move_rate"]["verdict"] == "improved"
    assert metrics["explanation_rate"]["verdict"] == "regressed"
    assert len(comparison["examples"]) == 12
    # The trade-off is visible as data on both runs.
    assert len(state["runs"]) == 2
    assert len(state["adapters"]) == 1

    # Benchmark eval rows land in the shared evals API too, scoped by
    # model and checkpoint, workspace-free.
    evals = client.get("/evals", params={"modality": "text"}).json()
    benchmark_rows = [row for row in evals if row["run_id"] is not None]
    assert benchmark_rows
    assert all(row["checkpoint"] in ("base", "gemma-chess-sft-v1") for row in benchmark_rows)


def test_train_against_a_room_snapshot_maps_to_409(client: TestClient):
    # Create real room data through the public routes, freeze it, then
    # ask the cached replay to pose as training on it.
    user = client.post("/users", json={"name": "Ada"}).json()
    workspace = client.post(
        "/workspaces", json={"user_id": user["id"], "page_slug": "chess-machine"}
    ).json()
    move = client.post(f"/workspaces/{workspace['id']}/moves", json={"uci": "e2e4"})
    assert move.status_code == 200

    frozen = client.post("/adaptation/snapshots", json={"label": "room-test"})
    assert frozen.status_code == 201
    body = frozen.json()
    assert body["origin"] == "frozen"
    assert body["row_count"] == 1
    assert body["label"] == "room-test"

    train = client.post(
        "/jobs",
        json={
            "job_type": "text.train_adapter",
            "params": {"dataset_snapshot_id": body["id"], "config_id": "text-gemma-lora-v1"},
        },
    )
    assert train.status_code == 409
    assert "bound to the reference snapshot" in train.json()["detail"]


def test_live_benchmark_without_credentials_maps_to_503(client: TestClient):
    state = client.get("/adaptation/state").json()
    suite = state["suites"][0]
    response = client.post(
        "/jobs",
        json={
            "job_type": "text.benchmark_eval",
            "params": {"suite_id": suite["id"], "checkpoint": "base", "source": "live"},
        },
    )
    assert response.status_code == 503


def test_cached_media_route_serves_committed_files_only(client: TestClient, tmp_path):
    missing = client.get("/artifacts/media/image/not_there.png")
    assert missing.status_code == 404
    traversal = client.get("/artifacts/media/image/..%2F..%2Fsecrets.png")
    assert traversal.status_code == 404
