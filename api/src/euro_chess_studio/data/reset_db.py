"""Command: drop and recreate the local SQLite database.

Run via `just reset-db`. Leaves the database empty; run `just seed`
afterwards to repopulate pages and cached fixtures.
"""

from euro_chess_studio.config import get_db_path
from euro_chess_studio.data.db import get_connection, init_db


def main() -> None:
    db_path = get_db_path()
    if db_path.exists():
        db_path.unlink()
    conn = get_connection(db_path)
    try:
        init_db(conn)
    finally:
        conn.close()
    print(f"reset {db_path}")


if __name__ == "__main__":
    main()
