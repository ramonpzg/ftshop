from pathlib import Path

from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.presenter_state_repo import (
    get_or_create_presenter_state,
    update_presenter_state,
)


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    return conn


def test_get_or_create_presenter_state_creates_default_row(tmp_path: Path):
    conn = make_conn(tmp_path)
    state = get_or_create_presenter_state(conn)
    assert state["mode"] == "idle"
    assert state["locked"] == 0
    assert state["active_page_slug"] is None


def test_get_or_create_presenter_state_is_idempotent(tmp_path: Path):
    conn = make_conn(tmp_path)
    get_or_create_presenter_state(conn)
    get_or_create_presenter_state(conn)
    rows = conn.execute("SELECT * FROM presenter_state").fetchall()
    assert len(rows) == 1


def test_update_presenter_state_only_changes_given_fields(tmp_path: Path):
    conn = make_conn(tmp_path)
    update_presenter_state(conn, mode="presenter", active_page_slug="presentation")
    updated = update_presenter_state(conn, locked=True)
    assert updated["mode"] == "presenter"
    assert updated["active_page_slug"] == "presentation"
    assert updated["locked"] == 1


def test_update_presenter_state_can_clear_active_page_slug(tmp_path: Path):
    conn = make_conn(tmp_path)
    update_presenter_state(conn, active_page_slug="presentation")
    updated = update_presenter_state(conn, mode="workspaces", active_page_slug=None)
    assert updated["active_page_slug"] is None
