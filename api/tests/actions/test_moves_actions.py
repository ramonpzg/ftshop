import json
from pathlib import Path

import chess
import pytest

from euro_chess_studio.actions.moves import WorkspaceNotFoundError, make_move
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


def test_make_move_updates_the_board_on_a_legal_move(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    result = make_move(conn, workspace["id"], "e2e4")
    assert result.move["is_legal"] == 1
    assert len(result.dataset_rows) == 6
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] != chess.STARTING_FEN


def test_make_move_rejects_an_illegal_move_without_changing_the_board(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    result = make_move(conn, workspace["id"], "e2e5")
    assert result.move["is_legal"] == 0
    assert result.dataset_rows == []
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] == chess.STARTING_FEN


def test_make_move_raises_for_unknown_workspace(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    with pytest.raises(WorkspaceNotFoundError):
        make_move(conn, "workspace_does_not_exist", "e2e4")


def test_make_move_commits_everything_or_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A failure after the move insert rolls the whole move back: no move
    row, no dataset rows, board unchanged, visible from a second
    connection because nothing was committed."""
    from euro_chess_studio.actions import moves as moves_action

    conn, workspace = make_workspace(tmp_path)
    conn.commit()

    def explode(*args, **kwargs):
        raise RuntimeError("simulated mid-transaction failure")

    monkeypatch.setattr(moves_action, "insert_dataset_row", explode)
    with pytest.raises(RuntimeError, match="simulated"):
        make_move(conn, workspace["id"], "e2e4")

    other = get_connection(tmp_path / "test.db")
    try:
        assert other.execute("SELECT COUNT(*) FROM moves").fetchone()[0] == 0
        assert other.execute("SELECT COUNT(*) FROM dataset_rows").fetchone()[0] == 0
        fen = other.execute("SELECT board_fen FROM workspaces").fetchone()[0]
        assert fen == chess.STARTING_FEN
    finally:
        other.close()


def test_make_move_persists_atomically_for_a_second_connection(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    conn.commit()
    make_move(conn, workspace["id"], "e2e4")

    other = get_connection(tmp_path / "test.db")
    try:
        assert other.execute("SELECT COUNT(*) FROM moves").fetchone()[0] == 1
        assert other.execute("SELECT COUNT(*) FROM dataset_rows").fetchone()[0] == 6
        fen = other.execute("SELECT board_fen FROM workspaces").fetchone()[0]
        assert fen != chess.STARTING_FEN
    finally:
        other.close()


def test_make_move_records_actor_and_model(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    yours = make_move(conn, workspace["id"], "e2e4")
    theirs = make_move(conn, workspace["id"], "e7e5", actor="model", model="gemma-4-2b-local")
    assert yours.move["actor"] == "participant"
    assert yours.move["model"] is None
    assert theirs.move["actor"] == "model"
    assert theirs.move["model"] == "gemma-4-2b-local"


def test_make_move_pgn_prefix_grows_across_a_sequence(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    make_move(conn, workspace["id"], "e2e4")
    result = make_move(conn, workspace["id"], "e7e5")
    dataset_by_shape = {row["shape"]: row for row in result.dataset_rows}
    payload = json.loads(dataset_by_shape["pgn_prefix_to_move"]["payload_json"])
    assert payload["prefix"] == "1. e4"
    assert payload["target_san"] == "e5"
