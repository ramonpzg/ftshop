"""Action-level export tests: the SFT file only trains on legitimate
targets, the full archive is self-contained and provenance-complete."""

import json
from pathlib import Path

import chess
import pytest

from euro_chess_studio.actions import model_turn as model_turn_module
from euro_chess_studio.actions.export import export_full_dataset, export_text_dataset
from euro_chess_studio.actions.model_turn import model_turn
from euro_chess_studio.actions.moves import make_move
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.llm_client import ChatOutcome
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.users_repo import insert_user
from euro_chess_studio.data.workspaces_repo import insert_workspace


def fake_outcome(content: str) -> ChatOutcome:
    return ChatOutcome(
        content=content,
        model="gpt-5.6-luna",
        provider_alias="opponent",
        attempts=1,
        request_ids=(),
        json_mode_requested=True,
        json_mode_sent=True,
        json_mode_dropped=False,
        reasoning_effort_dropped=False,
    )


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


def test_sft_export_excludes_fallback_moves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    conn, workspace = make_workspace(tmp_path)
    # Participant move: eligible.
    make_move(conn, workspace["id"], "e2e4")
    # Model move via a clean reply: eligible.
    monkeypatch.setattr(
        model_turn_module.llm_client, "chat", lambda *a, **k: fake_outcome('{"move": "e7e5"}')
    )
    model_turn(conn, workspace["id"])
    # A second model turn that never produces a legal reply: resolved by
    # the deterministic fallback, not eligible for training.
    monkeypatch.setattr(
        model_turn_module.llm_client, "chat", lambda *a, **k: fake_outcome("not json")
    )
    make_move(conn, workspace["id"], "g1f3")  # participant plays again
    result = model_turn(conn, workspace["id"])
    assert result.outcome == "fallback_move"

    monkeypatch.setenv("CHESS_STUDIO_DATA_DIR", str(tmp_path / "data"))
    export_result = export_text_dataset(conn)

    lines = [json.loads(line) for line in Path(export_result.path).read_text().strip().split("\n")]
    # Three real moves (participant e2e4, participant g1f3, model e7e5)
    # produced fen_legal_moves_to_move rows; the fallback move did not
    # make it into the SFT file.
    assert export_result.row_count == 3
    completions = {json.loads(line["completion"])["move"] for line in lines}
    assert completions == {"e2e4", "g1f3", "e7e5"}


def test_full_export_tags_every_row_with_move_provenance_and_eligibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    conn, workspace = make_workspace(tmp_path)
    participant_move = make_move(conn, workspace["id"], "e2e4").move
    monkeypatch.setattr(
        model_turn_module.llm_client, "chat", lambda *a, **k: fake_outcome("still not json")
    )
    monkeypatch.setenv("MODEL_TURN_MAX_ATTEMPTS", "1")
    fallback_result = model_turn(conn, workspace["id"])
    assert fallback_result.outcome == "fallback_move"
    fallback_move = fallback_result.move_result.move

    monkeypatch.setenv("CHESS_STUDIO_DATA_DIR", str(tmp_path / "data"))
    export_result = export_full_dataset(conn)
    lines = [json.loads(line) for line in Path(export_result.path).read_text().strip().split("\n")]

    by_move_id = {}
    for line in lines:
        by_move_id.setdefault(line["move_id"], []).append(line)

    participant_rows = by_move_id[participant_move["id"]]
    assert len(participant_rows) == 6
    assert all(row["actor"] == "participant" for row in participant_rows)
    assert all(row["training_eligible"] is True for row in participant_rows)
    assert all(row["game_id"] is None for row in participant_rows)  # free play

    fallback_rows = by_move_id[fallback_move["id"]]
    assert len(fallback_rows) == 6
    assert all(row["actor"] == "fallback" for row in fallback_rows)
    assert all(row["training_eligible"] is False for row in fallback_rows)
    assert all(row["model"] == "gpt-5.6-luna" for row in fallback_rows)

    # The tensor row is self-contained: the fen it was built from rides
    # along in the exported payload, not just the shape.
    tensor_row = next(
        row for row in participant_rows if row["shape"] == "board_tensor_to_move_class"
    )
    assert tensor_row["fen"] == chess.STARTING_FEN
