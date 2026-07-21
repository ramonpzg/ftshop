"""SQLite persistence: what an action writes, a fresh connection reads
back unchanged, and a database from the first release migrates in
place without losing games."""

import sqlite3

from conftest import fresh_connection

from chess_tui.data import attempts_repo, games_repo, plies_repo, settings_repo
from chess_tui.data.db import connect

V1_SCHEMA = """
CREATE TABLE games (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    result TEXT,
    termination TEXT,
    duration_seconds REAL
);
CREATE TABLE plies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL REFERENCES games(id),
    ply INTEGER NOT NULL, actor TEXT NOT NULL, uci TEXT NOT NULL, san TEXT NOT NULL,
    fen_before TEXT NOT NULL, fen_after TEXT NOT NULL, is_capture INTEGER NOT NULL,
    comment TEXT, created_at TEXT NOT NULL, UNIQUE (game_id, ply)
);
CREATE TABLE model_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL REFERENCES games(id),
    ply INTEGER NOT NULL, attempt INTEGER NOT NULL, corrective INTEGER NOT NULL,
    status TEXT NOT NULL, raw_reply TEXT, parsed_move TEXT, comment TEXT,
    request_id TEXT, latency_ms INTEGER, error_detail TEXT, created_at TEXT NOT NULL
);
"""


def test_game_ply_attempt_roundtrip_survives_reconnect(db_path):
    conn = connect(db_path)
    games_repo.insert_game(
        conn,
        "g1",
        "2026-07-21T10:00:00+00:00",
        "gemma-4-2b-local",
        "tui-move-v3",
        "black",
        "ramon",
    )
    plies_repo.insert_ply(
        conn,
        "g1",
        1,
        "model",
        "e2e4",
        "e4",
        "fen-before",
        "fen-after",
        False,
        "I will open. Watch closely.",
        "t1",
    )
    attempts_repo.insert_attempt(
        conn,
        "g1",
        1,
        1,
        False,
        "applied",
        '{"move":"e2e4","comment":"I will open. Watch closely."}',
        "e2e4",
        "I will open. Watch closely.",
        "chatcmpl-1",
        812,
        None,
        "t1",
    )
    games_repo.finish_game(conn, "g1", "2026-07-21T10:05:00+00:00", "0-1", "checkmate", 300.0)
    conn.commit()
    conn.close()

    other = fresh_connection(db_path)
    game = other.execute("SELECT * FROM games WHERE id = 'g1'").fetchone()
    assert game["result"] == "0-1"
    assert game["participant_color"] == "black"
    assert game["player_name"] == "ramon"
    plies = plies_repo.plies_for_game(other, "g1")
    assert plies[0]["comment"] == "I will open. Watch closely."
    attempts = attempts_repo.attempts_for_game(other, "g1")
    assert attempts[0]["latency_ms"] == 812
    other.close()


def test_v1_database_migrates_in_place_and_games_are_claimed(db_path):
    old = sqlite3.connect(db_path)
    old.executescript(V1_SCHEMA)
    old.execute(
        "INSERT INTO games (id, started_at, model, prompt_version, result, termination) "
        "VALUES ('old1', '2026-07-20T10:00:00+00:00', 'm', 'tui-move-v1', '1-0', 'checkmate')"
    )
    old.commit()
    old.close()

    conn = connect(db_path)  # migrates
    game = games_repo.get_game(conn, "old1")
    assert game["participant_color"] == "white"  # honest backfill: v1 was always White
    assert game["player_name"] is None

    games_repo.claim_unnamed_games(conn, "ramon")
    conn.commit()
    assert games_repo.get_game(conn, "old1")["player_name"] == "ramon"
    assert games_repo.game_results(conn, "ramon") == [("1-0", "white")]
    conn.close()


def test_settings_roundtrip(conn):
    assert settings_repo.get_setting(conn, "player_name") is None
    settings_repo.set_setting(conn, "player_name", "ramon")
    settings_repo.set_setting(conn, "player_name", "ramon p")
    conn.commit()
    assert settings_repo.get_setting(conn, "player_name") == "ramon p"


def test_repositories_do_not_commit(db_path):
    conn = connect(db_path)
    games_repo.insert_game(conn, "g1", "t0", "m", "v", "white", "x")
    other = fresh_connection(db_path)
    assert other.execute("SELECT COUNT(*) AS n FROM games").fetchone()["n"] == 0
    conn.rollback()
    assert conn.execute("SELECT COUNT(*) AS n FROM games").fetchone()["n"] == 0
    other.close()
    conn.close()


def test_attempt_numbering_is_per_game_and_ply(conn):
    games_repo.insert_game(conn, "g1", "t0", "m", "v", "white", "x")
    assert attempts_repo.next_attempt_number(conn, "g1", 2) == 1
    attempts_repo.insert_attempt(
        conn, "g1", 2, 1, False, "malformed_json", "?", None, None, None, 40, "bad", "t1"
    )
    assert attempts_repo.next_attempt_number(conn, "g1", 2) == 2
    assert attempts_repo.next_attempt_number(conn, "g1", 4) == 1


def test_history_lists_newest_first_filtered_by_player(conn):
    games_repo.insert_game(conn, "old", "2026-07-20T10:00:00+00:00", "m", "v", "white", "a")
    games_repo.insert_game(conn, "new", "2026-07-21T10:00:00+00:00", "m", "v", "black", "a")
    games_repo.insert_game(conn, "other", "2026-07-22T10:00:00+00:00", "m", "v", "white", "b")
    plies_repo.insert_ply(conn, "old", 1, "participant", "e2e4", "e4", "a", "b", False, None, "t")
    conn.commit()
    rows = games_repo.list_games_newest_first(conn, "a")
    assert [row["id"] for row in rows] == ["new", "old"]
    assert [row["ply_count"] for row in rows] == [0, 1]
    assert [row["participant_color"] for row in rows] == ["black", "white"]


def test_participant_captures_by_game(conn):
    games_repo.insert_game(conn, "g1", "t0", "m", "v", "black", "a")
    plies_repo.insert_ply(conn, "g1", 1, "model", "a", "a", "f", "f", True, None, "t")
    plies_repo.insert_ply(conn, "g1", 2, "participant", "b", "b", "f", "f", True, None, "t")
    plies_repo.insert_ply(conn, "g1", 3, "participant", "c", "c", "f", "f", False, None, "t")
    games_repo.finish_game(conn, "g1", "t1", "0-1", "checkmate", 60.0)
    conn.commit()
    assert plies_repo.participant_captures_by_game(conn, "a") == [("0-1", "black", 1)]
    assert plies_repo.participant_captures_by_game(conn, "nobody") == []
