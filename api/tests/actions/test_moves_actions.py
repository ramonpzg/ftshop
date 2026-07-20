import json
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import chess
import pytest

from euro_chess_studio.actions.errors import GameClockExpiredError, NotYourTurnError, StaleMoveError
from euro_chess_studio.actions.games import start_game
from euro_chess_studio.actions.moves import (
    MakeMoveResult,
    MovePrecondition,
    WorkspaceNotFoundError,
    make_move,
)
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.users_repo import insert_user
from euro_chess_studio.data.workspaces_repo import get_workspace, insert_workspace


def make_workspace(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    for page in PAGES:
        upsert_page(conn, page)
    page = conn.execute("SELECT * FROM pages WHERE slug = 'chess-machine'").fetchone()
    user = insert_user(conn, "Ada")
    workspace = insert_workspace(
        conn, "workspace_1", user["id"], page["id"], "shape:1", chess.STARTING_FEN
    )
    conn.commit()
    return conn, workspace


def test_make_move_updates_the_board_on_a_legal_move(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    result = make_move(conn, workspace["id"], "e2e4")
    assert result.move["is_legal"] == 1
    assert len(result.dataset_rows) == 6
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] != chess.STARTING_FEN


def test_make_move_rejects_an_illegal_move_without_changing_the_board(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    result = make_move(conn, workspace["id"], "e2e5")
    assert result.move["is_legal"] == 0
    assert result.dataset_rows == []
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] == chess.STARTING_FEN


def test_make_move_raises_for_unknown_workspace(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    with pytest.raises(WorkspaceNotFoundError):
        make_move(conn, "workspace_does_not_exist", "e2e4")


def test_make_move_commits_everything_or_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A failure after the move insert rolls the whole move back: no move
    row, no dataset rows, board unchanged, visible from a second
    connection because nothing was committed."""
    from euro_chess_studio.actions import moves as moves_action

    conn, workspace = make_workspace(tmp_path)
    conn.commit()

    def explode(*args, **kwargs):
        raise RuntimeError("simulated mid-transaction failure")

    monkeypatch.setattr(moves_action, "insert_dataset_row", explode)
    with pytest.raises(RuntimeError, match="simulated"):
        make_move(conn, workspace["id"], "e2e4")

    other = get_connection(tmp_path / "test.db")
    try:
        assert other.execute("SELECT COUNT(*) FROM moves").fetchone()[0] == 0
        assert other.execute("SELECT COUNT(*) FROM dataset_rows").fetchone()[0] == 0
        fen = other.execute("SELECT board_fen FROM workspaces").fetchone()[0]
        assert fen == chess.STARTING_FEN
    finally:
        other.close()


def test_make_move_persists_atomically_for_a_second_connection(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    conn.commit()
    make_move(conn, workspace["id"], "e2e4")

    other = get_connection(tmp_path / "test.db")
    try:
        assert other.execute("SELECT COUNT(*) FROM moves").fetchone()[0] == 1
        assert other.execute("SELECT COUNT(*) FROM dataset_rows").fetchone()[0] == 6
        fen = other.execute("SELECT board_fen FROM workspaces").fetchone()[0]
        assert fen != chess.STARTING_FEN
    finally:
        other.close()


def test_make_move_records_actor_and_model(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    yours = make_move(conn, workspace["id"], "e2e4")
    theirs = make_move(conn, workspace["id"], "e7e5", actor="model", model="gemma-4-2b-local")
    assert yours.move["actor"] == "participant"
    assert yours.move["model"] is None
    assert theirs.move["actor"] == "model"
    assert theirs.move["model"] == "gemma-4-2b-local"


def test_make_move_pgn_prefix_grows_across_a_sequence(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    make_move(conn, workspace["id"], "e2e4")
    result = make_move(conn, workspace["id"], "e7e5")
    dataset_by_shape = {row["shape"]: row for row in result.dataset_rows}
    payload = json.loads(dataset_by_shape["pgn_prefix_to_move"]["payload_json"])
    assert payload["prefix"] == "1. e4"
    assert payload["target_san"] == "e5"


def test_make_move_with_a_matching_precondition_applies_normally(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    precondition = MovePrecondition(fen=chess.STARTING_FEN, game_id=None, ply=0)
    result = make_move(conn, workspace["id"], "e2e4", precondition=precondition)
    assert result.move["is_legal"] == 1


def test_make_move_with_a_stale_precondition_refuses_and_touches_nothing(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    make_move(conn, workspace["id"], "e2e4")  # board moves on

    stale_precondition = MovePrecondition(fen=chess.STARTING_FEN, game_id=None, ply=0)
    with pytest.raises(StaleMoveError):
        make_move(conn, workspace["id"], "e7e5", precondition=stale_precondition)

    # Only the first move exists; the stale attempt left no trace.
    moves = conn.execute("SELECT uci FROM moves").fetchall()
    assert [m["uci"] for m in moves] == ["e2e4"]


def test_make_move_precondition_catches_a_ply_mismatch_at_the_same_fen(tmp_path: Path):
    """Same fen and game can recur (a fresh game after start-over resets
    to the starting position); ply distinguishes them."""
    conn, workspace = make_workspace(tmp_path)
    precondition = MovePrecondition(fen=chess.STARTING_FEN, game_id=None, ply=1)
    with pytest.raises(StaleMoveError):
        make_move(conn, workspace["id"], "e2e4", precondition=precondition)
    assert conn.execute("SELECT COUNT(*) FROM moves").fetchone()[0] == 0


def test_participant_cannot_play_the_models_color_in_an_active_game(tmp_path: Path):
    """Reproduces the reported bug: without a server-side turn check, a
    raw call could play both colors in a timed match, standing in for
    the model, bypassing its recovery state, and polluting participant
    metrics and the exported dataset with moves the model was supposed
    to make."""
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    make_move(conn, workspace["id"], "e2e4")  # participant, white: fine

    with pytest.raises(NotYourTurnError):
        make_move(conn, workspace["id"], "e7e5")  # participant playing black: rejected

    # Nothing was recorded for the rejected attempt; the board is
    # unchanged, still waiting on the model.
    moves = conn.execute("SELECT uci, actor FROM moves").fetchall()
    assert [(m["uci"], m["actor"]) for m in moves] == [("e2e4", "participant")]
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"].split(" ")[1] == "b"


def test_participant_may_play_both_colors_in_free_play(tmp_path: Path):
    """Free play has no model opponent to stand in for, so the turn
    check does not apply there."""
    conn, workspace = make_workspace(tmp_path)
    make_move(conn, workspace["id"], "e2e4")
    result = make_move(conn, workspace["id"], "e7e5")
    assert result.move["is_legal"] == 1
    assert result.move["actor"] == "participant"


def test_model_and_fallback_moves_succeed_on_their_own_turn(tmp_path: Path):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    make_move(conn, workspace["id"], "e2e4")
    model_result = make_move(conn, workspace["id"], "e7e5", actor="model", model="gpt-5.6-luna")
    assert model_result.move["is_legal"] == 1
    make_move(conn, workspace["id"], "g1f3")
    fallback_result = make_move(conn, workspace["id"], "b8c6", actor="fallback")
    assert fallback_result.move["is_legal"] == 1


def test_model_cannot_play_the_participants_color_in_an_active_game(tmp_path: Path):
    """The symmetric case of the bug above: only the participant side
    was rejected for playing the wrong color. A raw call standing in
    as the model (or its fallback) could play the participant's own
    move, e.g. an immediate White e2e4 the moment a timed game starts,
    with no model attempt ever recorded for it."""
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)

    with pytest.raises(NotYourTurnError):
        make_move(conn, workspace["id"], "e2e4", actor="model", model="gpt-5.6-luna")
    with pytest.raises(NotYourTurnError):
        make_move(conn, workspace["id"], "d2d4", actor="fallback")

    # Nothing was recorded for either rejected attempt; the board is
    # unchanged, still waiting on the participant.
    assert conn.execute("SELECT COUNT(*) FROM moves").fetchone()[0] == 0
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] == chess.STARTING_FEN


def test_clock_expiry_is_reconciled_after_the_write_lock_not_before(tmp_path: Path):
    """Reproduces the reported bug: the clock used to be checked before
    BEGIN IMMEDIATE, so a move that started while time remained could
    still lose the race for the write lock to another writer, and by
    the time that wait ended, the clock had genuinely run out without
    this call ever looking again. A second real connection grabs the
    write lock first and holds it comfortably longer than the little
    time left on the clock, so this call's own BEGIN IMMEDIATE blocks
    until well past expiry -- the clock check has to happen after that
    wait, not before it, to catch this."""
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 60)
    make_move(conn, workspace["id"], "e2e4")

    # ~0.2s left on the clock: still active right now, not for long.
    conn.execute(
        "UPDATE games SET started_at = ? WHERE workspace_id = ?",
        ((datetime.now(UTC) - timedelta(seconds=59.8)).isoformat(), workspace["id"]),
    )
    conn.commit()

    lock_acquired = threading.Event()

    def hold_the_lock() -> None:
        holder_conn = get_connection(tmp_path / "test.db")
        try:
            holder_conn.execute("BEGIN IMMEDIATE")
            lock_acquired.set()
            time.sleep(0.5)
            holder_conn.commit()
        finally:
            holder_conn.close()

    holder = threading.Thread(target=hold_the_lock)
    holder.start()
    assert lock_acquired.wait(timeout=5)

    # The 0.2s remaining on the clock is long gone by the time the
    # holder's 0.5s hold ends and this call's own BEGIN IMMEDIATE
    # finally returns.
    with pytest.raises(GameClockExpiredError):
        make_move(conn, workspace["id"], "e7e5", actor="model", model="stub")
    holder.join(timeout=5)

    game = conn.execute("SELECT * FROM games WHERE workspace_id = ?", (workspace["id"],)).fetchone()
    assert game["result"] == "loss_timeout"
    (count,) = conn.execute("SELECT COUNT(*) FROM moves WHERE ply = 1").fetchone()
    assert count == 0


def test_precondition_check_and_write_are_atomic_across_two_real_connections(tmp_path: Path):
    """A genuine two-connection race, not a nested call on one
    connection: two separate sqlite3 connections, synchronized with a
    barrier so both start make_move at the same instant, both decide
    the same move against the same precondition. Before BEGIN IMMEDIATE,
    each connection's read of the board happened before either had
    written anything, so both independently found the move legal
    against their own stale snapshot and both wrote -- reproduced
    exactly as reported: two overlapping model replies both recording
    a legal e7e5. Racing after the check (as an earlier test did, via a
    nested call inside a stubbed chat()) cannot exercise this window;
    only two real connections racing into the check itself can."""
    conn, workspace = make_workspace(tmp_path)
    make_move(conn, workspace["id"], "e2e4")
    conn.commit()

    precondition = MovePrecondition(
        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        game_id=None,
        ply=1,
    )
    barrier = threading.Barrier(2)
    results: list[object] = [None, None]

    def attempt(index: int) -> None:
        thread_conn = get_connection(tmp_path / "test.db")
        try:
            barrier.wait(timeout=5)
            results[index] = make_move(
                thread_conn,
                workspace["id"],
                "e7e5",
                actor="model",
                model="gpt-5.6-luna",
                precondition=precondition,
            )
        except Exception as exc:  # noqa: BLE001 -- captured for the assertions below
            results[index] = exc
        finally:
            thread_conn.close()

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    successes = [r for r in results if isinstance(r, MakeMoveResult)]
    stale_failures = [r for r in results if isinstance(r, StaleMoveError)]
    assert len(successes) == 1, results
    assert len(stale_failures) == 1, results

    other = get_connection(tmp_path / "test.db")
    try:
        # Exactly one legal move at this ply, not two duplicates.
        rows = other.execute("SELECT uci FROM moves WHERE ply = 1 AND is_legal = 1").fetchall()
        assert [r["uci"] for r in rows] == ["e7e5"]
    finally:
        other.close()
