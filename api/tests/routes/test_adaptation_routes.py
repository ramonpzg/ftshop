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
    assert state["live_benchmark"]["in_progress"] is False


def test_a_live_run_in_flight_is_shared_state_and_refuses_duplicates(
    client: TestClient, tmp_path, monkeypatch
):
    """The in-progress identity is durable and server-side: every
    client's poll sees it (a reloaded panel restores its waiting state
    from here), and a duplicate live run is refused with 409 before any
    provider call. A row past its expiry is a crashed run: invisible to
    the panel and no obstacle to the next run."""
    from datetime import UTC, datetime, timedelta

    from euro_chess_studio.calculations.generation import LIVE_BENCHMARK_LOCK_KEY
    from euro_chess_studio.data.db import get_connection
    from euro_chess_studio.data.run_locks_repo import insert_lock

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    suite_id = client.get("/adaptation/state").json()["suites"][0]["id"]

    conn = get_connection(tmp_path / "test.db")
    now = datetime.now(UTC)
    insert_lock(
        conn,
        LIVE_BENCHMARK_LOCK_KEY,
        acquired_at=now.isoformat(),
        expires_at=(now + timedelta(seconds=120)).isoformat(),
    )
    conn.commit()
    conn.close()

    assert client.get("/adaptation/state").json()["live_benchmark"]["in_progress"] is True

    duplicate = client.post(
        "/jobs",
        json={
            "job_type": "text.benchmark_eval",
            "params": {"suite_id": suite_id, "checkpoint": "base", "source": "live"},
        },
        headers={"x-forwarded-for": "127.0.0.1"},
    )
    assert duplicate.status_code == 409
    assert "already in progress" in duplicate.json()["detail"]

    # Expire the lock: the hung-process case. The panel unlocks and the
    # room is not stuck.
    conn = get_connection(tmp_path / "test.db")
    conn.execute(
        "UPDATE run_locks SET expires_at = ? WHERE lock_key = ?",
        ((now - timedelta(seconds=1)).isoformat(), LIVE_BENCHMARK_LOCK_KEY),
    )
    conn.commit()
    conn.close()
    assert client.get("/adaptation/state").json()["live_benchmark"]["in_progress"] is False


def test_a_backend_restart_clears_orphaned_live_run_locks(tmp_path, monkeypatch):
    """A lock that survives into a new process is orphaned by
    definition: the run it guarded died with the old process, and no
    restart can carry an in-flight run across. Waiting out the 330 s
    TTL would keep live controls dead mid-segment, so startup clears
    the table instead."""
    from datetime import UTC, datetime, timedelta

    from euro_chess_studio.calculations.generation import LIVE_BENCHMARK_LOCK_KEY
    from euro_chess_studio.data.db import get_connection
    from euro_chess_studio.data.run_locks_repo import insert_lock

    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with TestClient(app) as before_restart:
        conn = get_connection(tmp_path / "test.db")
        now = datetime.now(UTC)
        insert_lock(
            conn,
            LIVE_BENCHMARK_LOCK_KEY,
            acquired_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=330)).isoformat(),
        )
        conn.commit()
        conn.close()
        state = before_restart.get("/adaptation/state").json()
        assert state["live_benchmark"]["in_progress"] is True

    # The process dies mid-run and comes back: the same database, a
    # fresh lifespan. The lock must not outlive the run it guarded.
    with TestClient(app) as after_restart:
        state = after_restart.get("/adaptation/state").json()
        assert state["live_benchmark"]["in_progress"] is False


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
        # The proxy on the presenter's machine forwards the local browser.
        headers={"x-forwarded-for": "127.0.0.1"},
    )
    assert response.status_code == 503


def test_generation_is_refused_for_lan_clients(client: TestClient):
    """The full-room guardrail, enforced server-side: a browser that is
    not on the presenter's machine can spend neither the provider budget
    nor the presenter machine's compute, whatever the UI hides."""
    state = client.get("/adaptation/state").json()
    suite = state["suites"][0]
    lan = {"x-forwarded-for": "192.168.1.23"}
    live = client.post(
        "/jobs",
        json={
            "job_type": "text.benchmark_eval",
            "params": {"suite_id": suite["id"], "checkpoint": "base", "source": "live"},
        },
        headers=lan,
    )
    assert live.status_code == 403
    assert "presenter" in live.json()["detail"]
    generate = client.post(
        "/jobs",
        json={
            "job_type": "image.generate",
            "params": {"prompt": "a bishop", "model": "flux-2-klein"},
        },
        headers=lan,
    )
    assert generate.status_code == 403
    # Local audio synthesis spends the presenter machine's own CPU/GPU
    # and loads multi-GB models: refused for the room, and refused
    # BEFORE the runner, so this test can never start a real MusicGen
    # download on a machine that has the audio extra installed.
    local_audio = client.post(
        "/jobs",
        json={
            "job_type": "audio.generate",
            "params": {"prompt": "a click", "model": "musicgen-small"},
        },
        headers=lan,
    )
    assert local_audio.status_code == 403
    # Free jobs stay open to the room: a replayed benchmark from a LAN
    # client works.
    replay = client.post(
        "/jobs",
        json={"job_type": "text.benchmark_eval", "params": {"suite_id": suite["id"]}},
        headers=lan,
    )
    assert replay.status_code == 200


def test_the_forwarding_guard_cannot_be_spoofed_by_a_client_header(client: TestClient):
    """A LAN client that sends its own X-Forwarded-For gets the real
    peer APPENDED by the proxy, so the trustworthy hop is the last one.
    Trusting the first hop was the reported bypass."""
    spoofed = client.post(
        "/jobs",
        json={
            "job_type": "image.generate",
            "params": {"prompt": "a bishop", "model": "flux-2-klein"},
        },
        headers={"x-forwarded-for": "127.0.0.1, 192.168.1.23"},
    )
    assert spoofed.status_code == 403


def test_cached_media_route_serves_committed_files_only(client: TestClient, tmp_path):
    missing = client.get("/artifacts/media/image/not_there.png")
    assert missing.status_code == 404
    traversal = client.get("/artifacts/media/image/..%2F..%2Fsecrets.png")
    assert traversal.status_code == 404
