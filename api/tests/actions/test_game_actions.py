from pathlib import Path

import chess
import pytest

from euro_chess_studio.actions import game
from euro_chess_studio.actions.game import ModelReplyError, assess_position, model_move
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.users_repo import insert_user
from euro_chess_studio.data.workspaces_repo import get_workspace, insert_workspace


def make_workspace(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    for page in PAGES:
        upsert_page(conn, page)
    page = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    user = insert_user(conn, "Ada")
    workspace = insert_workspace(
        conn, "workspace_1", user["id"], page["id"], "shape:1", chess.STARTING_FEN
    )
    return conn, workspace


def test_model_move_applies_a_legal_reply(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    conn, workspace = make_workspace(tmp_path)
    monkeypatch.setattr(game.llm_client, "chat", lambda *a, **k: '{"move": "e2e4"}')

    result = model_move(conn, workspace["id"])

    assert result.move["is_legal"] == 1
    assert result.move["san"] == "e4"
    assert len(result.dataset_rows) > 0
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] != chess.STARTING_FEN


def test_model_move_records_an_illegal_reply_without_advancing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    conn, workspace = make_workspace(tmp_path)
    # Well-formed UCI, illegal from the start position. The environment
    # catches the model; the board must not move.
    monkeypatch.setattr(game.llm_client, "chat", lambda *a, **k: '{"move": "e2e5"}')

    result = model_move(conn, workspace["id"])

    assert result.move["is_legal"] == 0
    assert result.move["reward"] == -1
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] == chess.STARTING_FEN


def test_model_move_raises_on_unusable_reply(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    conn, workspace = make_workspace(tmp_path)
    monkeypatch.setattr(game.llm_client, "chat", lambda *a, **k: "I would castle early.")

    with pytest.raises(ModelReplyError):
        model_move(conn, workspace["id"])


def test_assess_position_returns_parsed_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    conn, workspace = make_workspace(tmp_path)
    monkeypatch.setattr(
        game.llm_client,
        "video_prompt_chat",
        lambda *a, **k: (
            '{"assessment": "Level.", "real_world": "Monday standup.", '
            '"video_prompt": "A team meets around a plain table."}'
        ),
    )

    result = assess_position(conn, workspace["id"])

    assert result["assessment"] == "Level."
    assert result["real_world"] == "Monday standup."
    assert result["video_prompt"] == "A team meets around a plain table."
    assert result["model"] == "gpt-5.6-luna"


def test_model_move_plays_with_the_games_chosen_opponent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from euro_chess_studio.actions.games import start_game

    conn, workspace = make_workspace(tmp_path)
    monkeypatch.setenv("OPPONENT_MODELS", "google/gemma-4-E2B-it-qat-q4_0-gguf")
    seen_models: list[str | None] = []

    def fake_chat(*args, **kwargs):
        seen_models.append(kwargs.get("model"))
        return '{"move": "e7e5"}'

    monkeypatch.setattr(game.llm_client, "chat", fake_chat)
    start_game(
        conn,
        workspace["id"],
        300,
        opponent_model="google/gemma-4-E2B-it-qat-q4_0-gguf",
    )
    from euro_chess_studio.actions.moves import make_move

    make_move(conn, workspace["id"], "e2e4")
    model_move(conn, workspace["id"])

    assert seen_models == ["google/gemma-4-E2B-it-qat-q4_0-gguf"]


def test_model_move_without_a_game_uses_the_default_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    conn, workspace = make_workspace(tmp_path)
    seen_models: list[str | None] = []

    def fake_chat(*args, **kwargs):
        seen_models.append(kwargs.get("model"))
        return '{"move": "e2e4"}'

    monkeypatch.setattr(game.llm_client, "chat", fake_chat)
    model_move(conn, workspace["id"])

    assert seen_models == [None]
