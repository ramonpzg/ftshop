"""SQLite access for the pages table. No business logic here."""

import sqlite3

from euro_chess_studio.calculations.ids import generate_id
from euro_chess_studio.calculations.pages import PageDef


def upsert_page(conn: sqlite3.Connection, page: PageDef) -> None:
    existing = conn.execute("SELECT id FROM pages WHERE slug = ?", (page.slug,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE pages SET title = ?, modality = ?, order_index = ? WHERE slug = ?",
            (page.title, page.modality, page.order_index, page.slug),
        )
    else:
        conn.execute(
            "INSERT INTO pages (id, slug, title, modality, order_index) VALUES (?, ?, ?, ?, ?)",
            (generate_id("page"), page.slug, page.title, page.modality, page.order_index),
        )
    conn.commit()


def list_pages(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM pages ORDER BY order_index").fetchall()


def get_page_by_slug(conn: sqlite3.Connection, slug: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM pages WHERE slug = ?", (slug,)).fetchone()
