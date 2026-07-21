"""SQLite persistence: what an action writes, a fresh connection reads
back unchanged, including model comments and raw replies."""

from conftest import fresh_connection

from chess_tui.data import attempts_repo, games_repo, plies_repo
from chess_tui.data.db import connect


def test_game_ply_attempt_roundtrip_survives_reconnect(db_path):
    conn = connect(db_path)
    games_repo.insert_game(
        conn, "g1", "2026-07-21T10:00:00+00:00", "gemma-4-2b-local", "tui-move-v1"
    )
    plies_repo.insert_ply(
        conn, "g1", 1, "participant", "e2e4", "e4", "fen-before", "fen-after", False, None, "t1"
    )
    plies_repo.insert_ply(
        conn,
        "g1",
        2,
        "model",
        "e7e5",
        "e5",
        "fen-after",
        "fen-later",
        False,
        "Symmetry. How brave.",
        "t2",
    )
    attempts_repo.insert_attempt(
        conn,
        "g1",
        2,
        1,
        False,
        "applied",
        '{"move":"e7e5","comment":"Symmetry. How brave."}',
        "e7e5",
        "Symmetry. How brave.",
        "chatcmpl-1",
        812,
        None,
        "t2",
    )
    games_repo.finish_game(conn, "g1", "2026-07-21T10:05:00+00:00", "1-0", "checkmate", 300.0)
    conn.commit()
    conn.close()

    other = fresh_connection(db_path)
    game = other.execute("SELECT * FROM games WHERE id = 'g1'").fetchone()
    assert game["result"] == "1-0"
    assert game["termination"] == "checkmate"
    assert game["prompt_version"] == "tui-move-v1"

    plies = plies_repo.plies_for_game(other, "g1")
    assert [row["san"] for row in plies] == ["e4", "e5"]
    assert plies[1]["comment"] == "Symmetry. How brave."

    attempts = attempts_repo.attempts_for_game(other, "g1")
    assert attempts[0]["raw_reply"] == '{"move":"e7e5","comment":"Symmetry. How brave."}'
    assert attempts[0]["latency_ms"] == 812
    other.close()


def test_repositories_do_not_commit(db_path):
    conn = connect(db_path)
    games_repo.insert_game(conn, "g1", "t0", "m", "v")
    other = fresh_connection(db_path)
    assert other.execute("SELECT COUNT(*) AS n FROM games").fetchone()["n"] == 0
    conn.rollback()
    assert conn.execute("SELECT COUNT(*) AS n FROM games").fetchone()["n"] == 0
    other.close()
    conn.close()


def test_attempt_numbering_is_per_game_and_ply(conn):
    games_repo.insert_game(conn, "g1", "t0", "m", "v")
    assert attempts_repo.next_attempt_number(conn, "g1", 2) == 1
    attempts_repo.insert_attempt(
        conn, "g1", 2, 1, False, "malformed_json", "?", None, None, None, 40, "bad", "t1"
    )
    assert attempts_repo.next_attempt_number(conn, "g1", 2) == 2
    assert attempts_repo.next_attempt_number(conn, "g1", 4) == 1


def test_history_lists_newest_first_with_ply_counts(conn):
    games_repo.insert_game(conn, "old", "2026-07-20T10:00:00+00:00", "m", "v")
    games_repo.insert_game(conn, "new", "2026-07-21T10:00:00+00:00", "m", "v")
    plies_repo.insert_ply(conn, "old", 1, "participant", "e2e4", "e4", "a", "b", False, None, "t")
    conn.commit()
    rows = games_repo.list_games_newest_first(conn)
    assert [row["id"] for row in rows] == ["new", "old"]
    assert [row["ply_count"] for row in rows] == [0, 1]


def test_participant_captures_by_game(conn):
    games_repo.insert_game(conn, "g1", "t0", "m", "v")
    plies_repo.insert_ply(conn, "g1", 1, "participant", "a", "a", "f", "f", True, None, "t")
    plies_repo.insert_ply(conn, "g1", 2, "model", "b", "b", "f", "f", True, None, "t")
    plies_repo.insert_ply(conn, "g1", 3, "participant", "c", "c", "f", "f", True, None, "t")
    games_repo.finish_game(conn, "g1", "t1", "1-0", "checkmate", 60.0)
    conn.commit()
    assert plies_repo.participant_captures_by_game(conn) == [("1-0", 2)]
