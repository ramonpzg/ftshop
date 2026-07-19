import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import chess
import pytest

from euro_chess_studio.actions.errors import (
    GameAlreadyActiveError,
    GameClockExpiredError,
    GameNotExpiredError,
    NoActiveGameError,
)
from euro_chess_studio.actions.games import flag_timeout, game_status, start_game, start_over
from euro_chess_studio.actions.moves import make_move
from euro_chess_studio.actions.presenter import reset_page
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.games_repo import get_active_game, insert_game
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


def expire_active_game(conn, workspace_id: str) -> None:
    """Backdates the active game's start so its clock has run out."""
    stale = (datetime.now(UTC) - timedelta(seconds=9000)).isoformat()
    conn.execute(
        "UPDATE games SET started_at = ? WHERE workspace_id = ? AND result IS NULL",
        (stale, workspace_id),
    )
    conn.commit()


def test_start_game_creates_an_active_game_and_resets_the_board(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    make_move(conn, workspace["id"], "e2e4")

    status = start_game(conn, workspace["id"], 300)

    assert status.game is not None
    assert status.game["result"] is None
    assert status.game["time_limit_seconds"] == 300
    assert status.workspace["board_fen"] == chess.STARTING_FEN
    assert status.record == {"wins": 0, "losses": 0, "draws": 0}


def test_starting_a_second_game_while_one_runs_is_refused(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    with pytest.raises(GameAlreadyActiveError):
        start_game(conn, workspace["id"], 300)


def test_start_over_records_a_resignation_loss_and_begins_a_fresh_game(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    first = start_game(conn, workspace["id"], 900)
    assert first.game is not None

    status = start_over(conn, workspace["id"])

    assert status.record == {"wins": 0, "losses": 1, "draws": 0}
    assert status.game is not None
    assert status.game["id"] != first.game["id"]
    # The new game keeps the clock the player chose.
    assert status.game["time_limit_seconds"] == 900
    assert status.workspace["board_fen"] == chess.STARTING_FEN
    finished = conn.execute("SELECT result FROM games WHERE result IS NOT NULL").fetchone()
    assert finished["result"] == "loss_resign"


def test_start_over_without_a_game_is_refused(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    with pytest.raises(NoActiveGameError):
        start_over(conn, workspace["id"])


def test_start_over_on_an_expired_clock_records_a_timeout_not_a_resignation(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    expire_active_game(conn, workspace["id"])

    status = start_over(conn, workspace["id"])

    assert status.record["losses"] == 1
    finished = conn.execute("SELECT result FROM games WHERE result IS NOT NULL").fetchone()
    assert finished["result"] == "loss_timeout"


def test_a_move_after_the_clock_ran_out_is_refused_and_the_game_is_lost(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    expire_active_game(conn, workspace["id"])

    with pytest.raises(GameClockExpiredError):
        make_move(conn, workspace["id"], "e2e4")

    assert get_active_game(conn, workspace["id"]) is None
    status = game_status(conn, workspace["id"])
    assert status.record == {"wins": 0, "losses": 1, "draws": 0}


def test_flag_timeout_records_the_loss_only_when_the_clock_really_ran_out(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)

    with pytest.raises(GameNotExpiredError):
        flag_timeout(conn, workspace["id"])

    expire_active_game(conn, workspace["id"])
    status = flag_timeout(conn, workspace["id"])
    assert status.game is None
    assert status.record["losses"] == 1


def test_flag_timeout_without_a_game_is_refused(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    with pytest.raises(NoActiveGameError):
        flag_timeout(conn, workspace["id"])


def test_game_status_lazily_expires_a_stale_game(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    expire_active_game(conn, workspace["id"])

    status = game_status(conn, workspace["id"])

    assert status.game is None
    assert status.record["losses"] == 1


def test_checkmate_by_the_player_wins_the_game(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    # Reversed fool's mate: white (the player) mates on move three.
    make_move(conn, workspace["id"], "e2e4", actor="participant")
    make_move(conn, workspace["id"], "f7f6", actor="model")
    make_move(conn, workspace["id"], "d2d4", actor="participant")
    make_move(conn, workspace["id"], "g7g5", actor="model")
    result = make_move(conn, workspace["id"], "d1h5", actor="participant")

    assert result.move["is_checkmate"] == 1
    assert result.game_result == "win"
    assert get_active_game(conn, workspace["id"]) is None
    assert game_status(conn, workspace["id"]).record["wins"] == 1


def test_checkmate_by_the_model_loses_the_game(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    # Fool's mate: black (the model) mates on move two.
    make_move(conn, workspace["id"], "f2f3", actor="participant")
    make_move(conn, workspace["id"], "e7e5", actor="model")
    make_move(conn, workspace["id"], "g2g4", actor="participant")
    result = make_move(conn, workspace["id"], "d8h4", actor="model")

    assert result.game_result == "loss"
    assert game_status(conn, workspace["id"]).record["losses"] == 1


def test_pgn_prefix_restarts_with_each_game(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    # Free play first: this history must not leak into the match.
    make_move(conn, workspace["id"], "d2d4")
    make_move(conn, workspace["id"], "d7d5")

    start_game(conn, workspace["id"], 300)
    make_move(conn, workspace["id"], "e2e4")
    result = make_move(conn, workspace["id"], "e7e5")

    by_shape = {row["shape"]: row for row in result.dataset_rows}
    payload = json.loads(by_shape["pgn_prefix_to_move"]["payload_json"])
    assert payload["prefix"] == "1. e4"
    assert payload["target_san"] == "e5"


def test_free_play_without_a_game_still_works_and_records_nothing(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    result = make_move(conn, workspace["id"], "e2e4")
    assert result.game_result is None
    assert result.move["game_id"] is None
    status = game_status(conn, workspace["id"])
    assert status.game is None
    assert status.record == {"wins": 0, "losses": 0, "draws": 0}


def test_reset_page_wipes_games_along_with_moves(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    make_move(conn, workspace["id"], "e2e4")
    start_over(conn, workspace["id"])

    reset_page(conn, "chess-machine")

    (games_left,) = conn.execute("SELECT COUNT(*) FROM games").fetchone()
    assert games_left == 0
    assert get_workspace(conn, workspace["id"])["board_fen"] == chess.STARTING_FEN


def test_init_db_adds_game_id_to_a_pre_games_moves_table(tmp_path: Path):
    conn = get_connection(tmp_path / "old.db")
    # A database from before the games feature: moves without game_id.
    conn.executescript(
        """
        CREATE TABLE moves (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            ply INTEGER NOT NULL,
            uci TEXT NOT NULL,
            san TEXT,
            fen_before TEXT NOT NULL,
            fen_after TEXT NOT NULL,
            is_legal INTEGER NOT NULL,
            is_check INTEGER NOT NULL,
            is_checkmate INTEGER NOT NULL,
            reward INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    init_db(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(moves)")}
    assert "game_id" in columns


def test_insert_game_accepts_a_backdated_start_for_tests(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    stale = (datetime.now(UTC) - timedelta(seconds=9000)).isoformat()
    game = insert_game(conn, workspace_id=workspace["id"], time_limit_seconds=300, started_at=stale)
    assert game["started_at"] == stale


def test_game_status_reports_a_timeout_that_happened_while_away(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    expire_active_game(conn, workspace["id"])

    first_look = game_status(conn, workspace["id"])
    second_look = game_status(conn, workspace["id"])

    # Only the read that discovered the timeout breaks the news.
    assert first_look.expired_while_away is True
    assert second_look.expired_while_away is False


def test_history_lists_finished_games_newest_first_with_move_counts(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    make_move(conn, workspace["id"], "e2e4")
    make_move(conn, workspace["id"], "e7e5")
    start_over(conn, workspace["id"])
    make_move(conn, workspace["id"], "d2d4")
    status = start_over(conn, workspace["id"])

    assert [row["result"] for row in status.history] == ["loss_resign", "loss_resign"]
    assert [row["legal_moves"] for row in status.history] == [1, 2]
    assert status.record["losses"] == 2
