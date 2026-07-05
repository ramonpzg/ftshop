"""FastAPI dependencies shared across routers."""

import sqlite3
from collections.abc import Iterator

from euro_chess_studio.data.db import get_connection


def get_db() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
