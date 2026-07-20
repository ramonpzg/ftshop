from pathlib import Path

import chess
import pytest

from euro_chess_studio.actions.errors import PageNotFoundError
from euro_chess_studio.actions.moves import make_move
from euro_chess_studio.actions.presenter import (
    bring_to_presenter_view,
    get_presenter_state,
    reset_page,
    send_to_workspaces,
    set_locked,
)
from euro_chess_studio.actions.workspaces import create_or_get_workspace, join_workshop
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.eval_results_repo import list_eval_results
from euro_chess_studio.data.moves_repo import list_moves
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.workspaces_repo import get_workspace
from euro_chess_studio.jobs.base import JobConfig
from euro_chess_studio.jobs.local_runner import LocalRunner


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    for page in PAGES:
        upsert_page(conn, page)
    return conn


def test_get_presenter_state_defaults_to_idle(tmp_path: Path):
    conn = make_conn(tmp_path)
    assert get_presenter_state(conn)["mode"] == "idle"


def test_bring_to_presenter_view_sets_mode_and_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    state = bring_to_presenter_view(conn, "presentation")
    assert state["mode"] == "presenter"
    assert state["active_page_slug"] == "presentation"


def test_bring_to_presenter_view_rejects_unknown_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    with pytest.raises(PageNotFoundError):
        bring_to_presenter_view(conn, "not-a-page")


def test_send_to_workspaces_clears_active_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    bring_to_presenter_view(conn, "presentation")
    state = send_to_workspaces(conn)
    assert state["mode"] == "workspaces"
    assert state["active_page_slug"] is None


def test_set_locked_toggles_the_flag(tmp_path: Path):
    conn = make_conn(tmp_path)
    assert set_locked(conn, True)["locked"] == 1
    assert set_locked(conn, False)["locked"] == 0


def test_reset_page_clears_moves_and_resets_board(tmp_path: Path):
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")
    make_move(conn, workspace["id"], "e2e4")

    count = reset_page(conn, "chess-machine")

    assert count == 1
    assert list_moves(conn, workspace["id"]) == []
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] == chess.STARTING_FEN


def test_reset_page_clears_stale_computed_eval_results(tmp_path: Path):
    """Reproduces the reported bug: a computed 1/1 result must not keep
    showing after the data behind it is wiped and a re-run finds
    nothing. Before the fix, an empty eval left the prior number on
    the panel because the job simply skipped persisting anything for
    an unavailable metric, and reset_page never touched eval_results
    at all."""
    conn = make_conn(tmp_path)
    user = join_workshop(conn, "Ada")
    workspace = create_or_get_workspace(conn, user["id"], "chess-machine")
    make_move(conn, workspace["id"], "e2e4")

    runner = LocalRunner()
    runner.run(
        conn, JobConfig(job_type="text.prompt_eval", params={}, workspace_id=workspace["id"])
    )
    before = list_eval_results(conn, modality="text", workspace_id=workspace["id"])
    assert any(row["metric"] == "legal_move_rate" and row["value"] == 1.0 for row in before)

    reset_page(conn, "chess-machine")

    # The reset alone must already clear it, before any re-run happens.
    after_reset = list_eval_results(conn, modality="text", workspace_id=workspace["id"])
    assert after_reset == []

    # And running the eval again over the now-empty workspace must not
    # resurrect the old number either.
    runner.run(
        conn, JobConfig(job_type="text.prompt_eval", params={}, workspace_id=workspace["id"])
    )
    after_rerun = list_eval_results(conn, modality="text", workspace_id=workspace["id"])
    assert after_rerun == []


def test_reset_page_rejects_unknown_page(tmp_path: Path):
    conn = make_conn(tmp_path)
    with pytest.raises(PageNotFoundError):
        reset_page(conn, "not-a-page")


def test_reset_page_with_no_workspaces_resets_nothing(tmp_path: Path):
    conn = make_conn(tmp_path)
    assert reset_page(conn, "chess-machine") == 0


def test_every_presenter_update_bumps_the_revision(tmp_path: Path):
    conn = make_conn(tmp_path)
    first = bring_to_presenter_view(conn, "presentation")
    second = set_locked(conn, True)
    third = send_to_workspaces(conn)
    assert first["revision"] < second["revision"] < third["revision"]


def test_bring_to_presenter_view_records_the_target(tmp_path: Path):
    conn = make_conn(tmp_path)
    state = bring_to_presenter_view(
        conn,
        "presentation",
        frame_id="shape:seed-presentation-16",
        bounds_json='{"x": 0.0, "y": 1400.0, "w": 1600.0, "h": 900.0}',
    )
    assert state["target_frame_id"] == "shape:seed-presentation-16"
    assert '"w": 1600.0' in state["target_bounds_json"]


def test_send_to_workspaces_clears_the_target(tmp_path: Path):
    conn = make_conn(tmp_path)
    bring_to_presenter_view(conn, "presentation", frame_id="shape:f", bounds_json="{}")
    state = send_to_workspaces(conn)
    assert state["target_frame_id"] is None
    assert state["target_bounds_json"] is None


def test_lock_does_not_disturb_the_navigation_target(tmp_path: Path):
    conn = make_conn(tmp_path)
    bring_to_presenter_view(conn, "presentation", frame_id="shape:f", bounds_json="{}")
    state = set_locked(conn, True)
    assert state["target_frame_id"] == "shape:f"
    assert state["mode"] == "presenter"
