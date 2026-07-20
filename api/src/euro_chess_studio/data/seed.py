"""Command: populate the local database with static seed data.

Run via `just seed`, after `just reset-db` on a fresh database.
Safe to re-run: page upserts are idempotent by slug, and cached eval rows
are cleared and re-inserted rather than duplicated.
"""

import json
import sqlite3

from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.config import get_artifacts_dir
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.eval_results_repo import delete_cached_eval_results, insert_eval_result
from euro_chess_studio.data.pages_repo import upsert_page

CACHED_EVAL_MODALITIES = ["text", "image", "audio", "video"]


def seed_cached_evals(conn: sqlite3.Connection) -> int:
    """Clears and re-inserts the cached fixture rows, then commits: this
    is a seeding command, so it owns its own transaction."""
    delete_cached_eval_results(conn)
    count = 0
    for modality in CACHED_EVAL_MODALITIES:
        path = get_artifacts_dir() / "cached" / modality / "evals.json"
        entries = json.loads(path.read_text())
        for entry in entries:
            insert_eval_result(
                conn,
                modality=modality,
                metric=entry["metric"],
                value=entry["value"],
                workspace_id=None,
                source="cached",
                # The fixture's own explanation of why the number is
                # illustrative. It survives storage, the API, and the
                # panel; a cached value never poses as a live one.
                note=entry.get("note"),
            )
            count += 1
    conn.commit()
    return count


def main() -> None:
    # Imported here rather than at module top: seed.py is a data module,
    # and the adaptation seeding is an action composing calculations and
    # several repos. The command composes both; the module boundary stays.
    from euro_chess_studio.actions.adaptation import seed_adaptation_fixtures

    conn = get_connection()
    try:
        init_db(conn)
        for page in PAGES:
            upsert_page(conn, page)
        eval_count = seed_cached_evals(conn)
        adaptation_count = seed_adaptation_fixtures(conn)
        conn.commit()
        print(
            f"seeded {len(PAGES)} pages, {eval_count} cached eval results, "
            f"and {adaptation_count} adaptation fixtures"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
