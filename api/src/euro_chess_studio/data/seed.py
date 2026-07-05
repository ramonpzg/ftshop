"""Command: populate the local database with static seed data.

Run via `just seed`, after `just reset-db` on a fresh database.
Safe to re-run: page upserts are idempotent by slug.
"""

from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import upsert_page


def main() -> None:
    conn = get_connection()
    try:
        init_db(conn)
        for page in PAGES:
            upsert_page(conn, page)
        print(f"seeded {len(PAGES)} pages")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
