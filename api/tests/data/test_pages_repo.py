from pathlib import Path

from euro_chess_studio.calculations.pages import PAGES, PageDef
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import get_page_by_slug, list_pages, upsert_page


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    return conn


def test_upsert_page_inserts_new_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    upsert_page(conn, PAGES[0])
    row = get_page_by_slug(conn, PAGES[0].slug)
    assert row is not None
    assert row["title"] == PAGES[0].title
    assert row["modality"] == PAGES[0].modality


def test_upsert_page_is_idempotent_by_slug(tmp_path: Path):
    conn = make_conn(tmp_path)
    upsert_page(conn, PAGES[0])
    upsert_page(conn, PAGES[0])
    rows = conn.execute("SELECT * FROM pages WHERE slug = ?", (PAGES[0].slug,)).fetchall()
    assert len(rows) == 1


def test_upsert_page_updates_existing_row(tmp_path: Path):
    conn = make_conn(tmp_path)
    upsert_page(conn, PAGES[0])
    renamed = PageDef(PAGES[0].slug, "New Title", PAGES[0].modality, PAGES[0].order_index)
    upsert_page(conn, renamed)
    row = get_page_by_slug(conn, PAGES[0].slug)
    assert row["title"] == "New Title"


def test_list_pages_returns_all_in_order(tmp_path: Path):
    conn = make_conn(tmp_path)
    for page in PAGES:
        upsert_page(conn, page)
    rows = list_pages(conn)
    assert [row["slug"] for row in rows] == [p.slug for p in PAGES]
