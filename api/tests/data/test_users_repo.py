from pathlib import Path

from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.users_repo import get_user, insert_user, list_users


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    return conn


def test_insert_user_generates_id_and_stores_name(tmp_path: Path):
    conn = make_conn(tmp_path)
    row = insert_user(conn, "Ada")
    assert row["id"].startswith("user_")
    assert row["name"] == "Ada"


def test_get_user_returns_none_for_unknown_id(tmp_path: Path):
    conn = make_conn(tmp_path)
    assert get_user(conn, "user_does_not_exist") is None


def test_list_users_orders_by_creation(tmp_path: Path):
    conn = make_conn(tmp_path)
    insert_user(conn, "Ada")
    insert_user(conn, "Grace")
    names = [row["name"] for row in list_users(conn)]
    assert names == ["Ada", "Grace"]
