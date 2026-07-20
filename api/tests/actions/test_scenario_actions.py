"""Scenario mapping persistence: suggestions, review, failure states,
reload, and export all keep raw and approved values separate."""

import json
from pathlib import Path

import chess
import pytest

from euro_chess_studio.actions import scenario as scenario_module
from euro_chess_studio.actions.errors import (
    ModelReplyError,
    ScenarioNotFoundError,
    ScenarioReviewError,
    WorkspaceNotFoundError,
)
from euro_chess_studio.actions.export import export_scenarios
from euro_chess_studio.actions.scenario import (
    latest_scenario_for_workspace,
    review_scenario,
    suggest_scenario,
)
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.llm_client import ChatOutcome, LlmRequestError
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.users_repo import insert_user
from euro_chess_studio.data.workspaces_repo import insert_workspace

GOOD_REPLY = (
    '{"assessment": "Level.", "real_world": "A new hire watches the routine '
    'before touching anything.", "video_prompt": "A documentary shot follows '
    'an analyst through a quiet control room."}'
)


def fake_outcome(
    content: str,
    *,
    attempts: int = 1,
    json_mode_dropped: bool = False,
    reasoning_effort_dropped: bool = False,
) -> ChatOutcome:
    return ChatOutcome(
        content=content,
        model="gpt-5.6-luna",
        provider_alias="video_prompt",
        attempts=attempts,
        request_ids=("req-scene",),
        json_mode_requested=True,
        json_mode_sent=True,
        json_mode_dropped=json_mode_dropped,
        reasoning_effort_dropped=reasoning_effort_dropped,
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


def stub_reply(monkeypatch: pytest.MonkeyPatch, reply):
    def fake_video_prompt_chat(messages, **kwargs):
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(scenario_module.llm_client, "video_prompt_chat", fake_video_prompt_chat)


def test_suggestion_is_persisted_with_raw_reply_and_provenance(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_reply(monkeypatch, fake_outcome(GOOD_REPLY))

    scenario = suggest_scenario(conn, workspace["id"])

    assert scenario["status"] == "suggested"
    assert scenario["suggested_assessment"] == "Level."
    assert scenario["model"] == "gpt-5.6-luna"
    assert scenario["provider_alias"] == "video_prompt"
    assert scenario["prompt_version"] == "assess-v1"
    assert scenario["ply"] == 0
    attempt = conn.execute(
        "SELECT * FROM model_attempts WHERE id = ?", (scenario["attempt_id"],)
    ).fetchone()
    assert attempt["task"] == "scenario"
    assert attempt["raw_response"] == GOOD_REPLY
    assert attempt["parse_ok"] == 1


def test_capability_fallback_provenance_is_persisted_not_discarded(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_reply(
        monkeypatch,
        fake_outcome(GOOD_REPLY, attempts=2, json_mode_dropped=True),
    )

    scenario = suggest_scenario(conn, workspace["id"])

    attempt = conn.execute(
        "SELECT * FROM model_attempts WHERE id = ?", (scenario["attempt_id"],)
    ).fetchone()
    assert attempt["transport_attempts"] == 2
    assert attempt["json_mode_dropped"] == 1
    assert attempt["reasoning_effort_dropped"] == 0


def test_reload_restores_the_latest_scenario(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_reply(monkeypatch, fake_outcome(GOOD_REPLY))
    suggested = suggest_scenario(conn, workspace["id"])

    other = get_connection(tmp_path / "test.db")
    try:
        restored = latest_scenario_for_workspace(other, workspace["id"])
        assert restored is not None
        assert restored["id"] == suggested["id"]
        assert restored["suggested_video_prompt"] == suggested["suggested_video_prompt"]
    finally:
        other.close()


def test_accept_copies_the_suggestion_without_touching_it(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_reply(monkeypatch, fake_outcome(GOOD_REPLY))
    suggested = suggest_scenario(conn, workspace["id"])

    reviewed = review_scenario(conn, suggested["id"], accept=True)

    assert reviewed["status"] == "accepted"
    assert reviewed["final_assessment"] == reviewed["suggested_assessment"]
    assert reviewed["suggested_assessment"] == "Level."


def test_edit_keeps_the_raw_suggestion_intact(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_reply(monkeypatch, fake_outcome(GOOD_REPLY))
    suggested = suggest_scenario(conn, workspace["id"])

    reviewed = review_scenario(
        conn,
        suggested["id"],
        accept=False,
        assessment="Sharper.",
        real_world="A trainee shadows the night shift.",
        video_prompt="A handheld shot tracks a trainee through a server room.",
    )

    assert reviewed["status"] == "edited"
    assert reviewed["final_assessment"] == "Sharper."
    assert reviewed["suggested_assessment"] == "Level."
    assert reviewed["suggested_video_prompt"].startswith("A documentary shot")


def test_edit_with_missing_fields_is_rejected(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_reply(monkeypatch, fake_outcome(GOOD_REPLY))
    suggested = suggest_scenario(conn, workspace["id"])

    with pytest.raises(ScenarioReviewError):
        review_scenario(conn, suggested["id"], accept=False, assessment="only one field")


def test_parse_failure_records_raw_and_does_not_erase_prior_records(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_reply(monkeypatch, fake_outcome(GOOD_REPLY))
    good = suggest_scenario(conn, workspace["id"])

    stub_reply(monkeypatch, fake_outcome("the position is fine I think"))
    with pytest.raises(ModelReplyError):
        suggest_scenario(conn, workspace["id"])

    rows = conn.execute("SELECT * FROM scenario_assessments ORDER BY created_at").fetchall()
    assert [row["status"] for row in rows] == ["suggested", "failed"]
    failed_attempt = conn.execute(
        "SELECT * FROM model_attempts WHERE id = ?", (rows[1]["attempt_id"],)
    ).fetchone()
    assert failed_attempt["raw_response"] == "the position is fine I think"
    # The prior good suggestion is untouched in the database (still
    # there, still queryable), but reload surfaces the true latest
    # state -- the failure -- rather than silently reverting to a
    # suggestion that predates the participant's most recent move.
    latest = latest_scenario_for_workspace(conn, workspace["id"])
    assert latest["id"] != good["id"]
    assert latest["status"] == "failed"
    assert latest["error_detail"] == "reply had no usable assessment"
    assert (
        conn.execute("SELECT * FROM scenario_assessments WHERE id = ?", (good["id"],)).fetchone()[
            "suggested_assessment"
        ]
        == good["suggested_assessment"]
    )


def test_transport_failure_has_a_recoverable_persisted_state(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_reply(
        monkeypatch,
        LlmRequestError(
            "502 from video_prompt",
            request_ids=("req-x",),
            transport_attempts=3,
            json_mode_dropped=True,
        ),
    )

    with pytest.raises(LlmRequestError):
        suggest_scenario(conn, workspace["id"])

    row = conn.execute("SELECT * FROM scenario_assessments").fetchone()
    assert row["status"] == "failed"
    assert "502" in row["error_detail"]
    # The same capability-fallback and transport-attempt provenance a
    # success carries (see the test above) must survive a terminal
    # failure too, not just get thrown away with the exception.
    attempt = conn.execute(
        "SELECT * FROM model_attempts WHERE id = ?", (row["attempt_id"],)
    ).fetchone()
    assert attempt["transport_attempts"] == 3
    assert attempt["json_mode_dropped"] == 1
    # Recovery is asking again; the failed row stays as history.
    stub_reply(monkeypatch, fake_outcome(GOOD_REPLY))
    scenario = suggest_scenario(conn, workspace["id"])
    assert scenario["status"] == "suggested"
    (count,) = conn.execute("SELECT COUNT(*) FROM scenario_assessments").fetchone()
    assert count == 2


def test_review_of_failed_or_unknown_scenarios_is_rejected(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_reply(monkeypatch, LlmRequestError("down", request_ids=()))
    with pytest.raises(LlmRequestError):
        suggest_scenario(conn, workspace["id"])
    failed = conn.execute("SELECT * FROM scenario_assessments").fetchone()

    with pytest.raises(ScenarioReviewError):
        review_scenario(conn, failed["id"], accept=True)
    with pytest.raises(ScenarioNotFoundError):
        review_scenario(conn, "scenario_nope", accept=True)


def test_unknown_workspace_raises(tmp_path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    with pytest.raises(WorkspaceNotFoundError):
        latest_scenario_for_workspace(conn, "workspace_nope")


def test_export_separates_raw_suggestions_from_approved_examples(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    monkeypatch.setenv("CHESS_STUDIO_DATA_DIR", str(tmp_path / "data"))
    stub_reply(monkeypatch, fake_outcome(GOOD_REPLY))
    first = suggest_scenario(conn, workspace["id"])
    review_scenario(conn, first["id"], accept=True)
    stub_reply(monkeypatch, fake_outcome(GOOD_REPLY))
    suggest_scenario(conn, workspace["id"])

    result = export_scenarios(conn)

    assert result.row_count == 2
    lines = [json.loads(line) for line in open(result.path)]
    accepted, raw_only = lines
    assert accepted["status"] == "accepted"
    assert accepted["approved"]["assessment"] == "Level."
    assert accepted["suggested"]["assessment"] == "Level."
    assert accepted["prompt_version"] == "assess-v1"
    assert raw_only["status"] == "suggested"
    assert raw_only["approved"] is None
