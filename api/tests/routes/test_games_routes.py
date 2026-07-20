from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from euro_chess_studio.data.db import get_connection
from euro_chess_studio.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CHESS_STUDIO_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


def make_workspace(client: TestClient) -> str:
    user = client.post("/users", json={"name": "Ada"}).json()
    workspace = client.post(
        "/workspaces", json={"user_id": user["id"], "page_slug": "chess-machine"}
    ).json()
    return workspace["id"]


def expire_active_game(tmp_path: Path, workspace_id: str) -> None:
    conn = get_connection(tmp_path / "test.db")
    stale = (datetime.now(UTC) - timedelta(seconds=9000)).isoformat()
    conn.execute(
        "UPDATE games SET started_at = ? WHERE workspace_id = ? AND result IS NULL",
        (stale, workspace_id),
    )
    conn.commit()
    conn.close()


def test_game_status_starts_empty(client: TestClient):
    workspace_id = make_workspace(client)
    body = client.get(f"/workspaces/{workspace_id}/game").json()
    assert body["game"] is None
    assert body["record"] == {"wins": 0, "losses": 0, "draws": 0}
    assert body["board_fen"].startswith("rnbqkbnr")


def test_start_game_defaults_to_five_minutes(client: TestClient):
    workspace_id = make_workspace(client)
    response = client.post(f"/workspaces/{workspace_id}/game/start", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["game"]["time_limit_seconds"] == 300
    assert 299 <= body["game"]["seconds_left"] <= 300


def test_start_game_rejects_a_clock_beyond_thirty_minutes(client: TestClient):
    workspace_id = make_workspace(client)
    response = client.post(
        f"/workspaces/{workspace_id}/game/start", json={"time_limit_seconds": 2400}
    )
    assert response.status_code == 422


def test_start_while_running_conflicts(client: TestClient):
    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/game/start", json={})
    response = client.post(f"/workspaces/{workspace_id}/game/start", json={})
    assert response.status_code == 409


def test_start_over_counts_the_loss(client: TestClient):
    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/game/start", json={"time_limit_seconds": 600})
    response = client.post(f"/workspaces/{workspace_id}/game/start-over")
    assert response.status_code == 200
    body = response.json()
    assert body["record"]["losses"] == 1
    assert body["game"]["time_limit_seconds"] == 600
    assert body["board_fen"].startswith("rnbqkbnr")


def test_start_over_without_a_game_conflicts(client: TestClient):
    workspace_id = make_workspace(client)
    response = client.post(f"/workspaces/{workspace_id}/game/start-over")
    assert response.status_code == 409


def test_timeout_needs_a_really_expired_clock(client: TestClient, tmp_path: Path):
    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/game/start", json={})

    early = client.post(f"/workspaces/{workspace_id}/game/timeout")
    assert early.status_code == 409

    expire_active_game(tmp_path, workspace_id)
    flagged = client.post(f"/workspaces/{workspace_id}/game/timeout")
    assert flagged.status_code == 200
    assert flagged.json()["record"]["losses"] == 1
    assert flagged.json()["game"] is None


def test_a_move_on_an_expired_clock_returns_409_and_the_loss_sticks(
    client: TestClient, tmp_path: Path
):
    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/game/start", json={})
    expire_active_game(tmp_path, workspace_id)

    response = client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "e2e4"})
    assert response.status_code == 409

    status = client.get(f"/workspaces/{workspace_id}/game").json()
    assert status["record"]["losses"] == 1


def test_a_checkmating_move_reports_the_game_result(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    from euro_chess_studio.actions import model_turn as model_turn_module
    from euro_chess_studio.data.llm_client import ChatOutcome

    def fake_outcome(content: str) -> ChatOutcome:
        return ChatOutcome(
            content=content,
            model="gpt-5.6-luna",
            provider_alias="opponent",
            attempts=1,
            request_ids=(),
            json_mode_requested=True,
            json_mode_sent=True,
            json_mode_dropped=False,
            reasoning_effort_dropped=False,
        )

    # Black's moves must come from the model, not the participant's own
    # endpoint: in an active game the server now enforces whose turn it
    # is (see actions/moves.py NotYourTurnError).
    black_replies = iter(['{"move": "f7f6"}', '{"move": "g7g5"}'])
    monkeypatch.setattr(
        model_turn_module.llm_client,
        "chat",
        lambda *a, **k: fake_outcome(next(black_replies)),
    )

    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/game/start", json={})
    client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "e2e4"})
    client.post(f"/workspaces/{workspace_id}/model-move")
    client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "d2d4"})
    client.post(f"/workspaces/{workspace_id}/model-move")
    response = client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "d1h5"})
    body = response.json()
    # The model played black; checkmate by the participant (white) is a win.
    assert body["game_result"] == "win"
    status = client.get(f"/workspaces/{workspace_id}/game").json()
    assert status["record"]["wins"] == 1
    assert status["game"] is None


def test_model_move_on_the_participants_turn_returns_409(client: TestClient):
    """Reproduces the reported bug end to end through the route: without
    a server-side check, /model-move could immediately play White's
    opening move the moment a timed game started."""
    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/game/start", json={})

    response = client.post(f"/workspaces/{workspace_id}/model-move")

    assert response.status_code == 409
    state = client.get(f"/workspaces/{workspace_id}/state").json()
    assert state["moves"] == []


def test_game_status_on_unknown_workspace_is_404(client: TestClient):
    response = client.get("/workspaces/nope/game")
    assert response.status_code == 404


def test_status_breaks_the_news_of_an_expiry_and_lists_history(client: TestClient, tmp_path: Path):
    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/game/start", json={})
    client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "e2e4"})
    expire_active_game(tmp_path, workspace_id)

    first = client.get(f"/workspaces/{workspace_id}/game").json()
    assert first["expired_while_away"] is True
    assert first["game"] is None
    assert first["history"][0]["result"] == "loss_timeout"
    assert first["history"][0]["legal_moves"] == 1

    second = client.get(f"/workspaces/{workspace_id}/game").json()
    assert second["expired_while_away"] is False


def test_presenter_dashboard_lists_the_room_and_expires_stale_clocks(
    client: TestClient, tmp_path: Path
):
    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/game/start", json={})
    client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "e2e4"})

    body = client.get("/presenter/games").json()
    assert body["playing"] == 1
    assert body["finished"] == 0
    assert body["games"][0]["user_name"] == "Ada"
    assert body["games"][0]["legal_moves"] == 1
    assert body["games"][0]["dataset_rows"] == 6
    assert body["games"][0]["seconds_left"] is not None
    # Free-play rows would also count here; this game produced all six.
    assert body["total_dataset_rows"] == 6

    expire_active_game(tmp_path, workspace_id)
    after = client.get("/presenter/games").json()
    assert after["playing"] == 0
    assert after["finished"] == 1
    assert after["games"][0]["result"] == "loss_timeout"
    assert after["games"][0]["seconds_left"] is None


def test_full_export_carries_every_shape_with_provenance(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("CHESS_STUDIO_DATA_DIR", str(tmp_path / "data"))
    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "e2e4"})

    response = client.post("/datasets/text/export-full")
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 6

    download = client.get(body["url"])
    assert download.status_code == 200
    import json as _json

    lines = [_json.loads(line) for line in download.text.strip().split("\n")]
    assert {line["shape"] for line in lines} == {
        "pgn_prefix_to_move",
        "fen_to_move",
        "fen_legal_moves_to_move",
        "board_tensor_to_move_class",
        "policy_move_reward",
        "rl_trajectory",
    }
    # Every row is traceable back to the move that produced it, and
    # flagged for whether it is a legitimate training target.
    assert all(line["actor"] == "participant" for line in lines)
    assert all(line["training_eligible"] is True for line in lines)
    assert all(line["move_id"] for line in lines)
    assert all(line["model"] is None for line in lines)  # a participant move has no model
    assert all(line["workspace_id"] == workspace_id for line in lines)


def test_start_game_records_the_chosen_opponent(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPPONENT_MODELS", "google/gemma-4-E2B-it-qat-q4_0-gguf,openai/gpt-5.6")
    workspace_id = make_workspace(client)

    status = client.get("/llm/status").json()
    assert status["opponent_models"] == [
        "google/gemma-4-E2B-it-qat-q4_0-gguf",
        "openai/gpt-5.6",
        "gpt-5.6-luna",
    ]

    response = client.post(
        f"/workspaces/{workspace_id}/game/start",
        json={"opponent_model": "google/gemma-4-E2B-it-qat-q4_0-gguf"},
    )
    assert response.status_code == 200
    assert response.json()["game"]["opponent_model"] == "google/gemma-4-E2B-it-qat-q4_0-gguf"

    # Start over keeps the same opponent.
    again = client.post(f"/workspaces/{workspace_id}/game/start-over").json()
    assert again["game"]["opponent_model"] == "google/gemma-4-E2B-it-qat-q4_0-gguf"


def test_start_game_rejects_a_model_not_on_offer(client: TestClient):
    workspace_id = make_workspace(client)
    response = client.post(
        f"/workspaces/{workspace_id}/game/start",
        json={"opponent_model": "made-up/nonsense"},
    )
    assert response.status_code == 422


def test_a_failed_assessment_survives_reload_as_an_explicit_failed_state(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    """Reproduces the reported bug: a failed scenario used to be
    excluded from the reload read, so reloading the page after a failed
    assessment silently showed the pristine empty state instead of the
    same recoverable failure a live attempt shows."""
    from euro_chess_studio.actions import scenario as scenario_module
    from euro_chess_studio.data.llm_client import LlmRequestError

    def fail_video_prompt_chat(*args, **kwargs):
        raise LlmRequestError("502 from video_prompt", request_ids=())

    monkeypatch.setattr(scenario_module.llm_client, "video_prompt_chat", fail_video_prompt_chat)

    workspace_id = make_workspace(client)
    client.post(f"/workspaces/{workspace_id}/moves", json={"uci": "e2e4"})
    assess_response = client.post(f"/workspaces/{workspace_id}/assess")
    assert assess_response.status_code == 502

    reload_response = client.get(f"/workspaces/{workspace_id}/scenario")
    assert reload_response.status_code == 200
    body = reload_response.json()
    assert body is not None
    assert body["status"] == "failed"
    assert "502" in body["error_detail"]
