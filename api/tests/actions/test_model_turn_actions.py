"""State machine tests for the model's turn: every failure mode has a
recorded attempt and a deterministic outcome. The transport is stubbed
at the action boundary; the transport itself is tested against
httpx.MockTransport in tests/data/test_llm_client.py."""

from pathlib import Path

import chess
import pytest

from euro_chess_studio.actions import model_turn as model_turn_module
from euro_chess_studio.actions.errors import GameClockExpiredError
from euro_chess_studio.actions.games import start_game
from euro_chess_studio.actions.model_turn import ModelTurnError, model_turn
from euro_chess_studio.actions.moves import make_move
from euro_chess_studio.calculations.pages import PAGES
from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.llm_client import ChatOutcome, LlmRequestError
from euro_chess_studio.data.model_attempts_repo import list_attempts
from euro_chess_studio.data.pages_repo import upsert_page
from euro_chess_studio.data.users_repo import insert_user
from euro_chess_studio.data.workspaces_repo import get_workspace, insert_workspace


def fake_outcome(
    content: str,
    model: str = "gpt-5.6-luna",
    *,
    attempts: int = 1,
    json_mode_dropped: bool = False,
    reasoning_effort_dropped: bool = False,
) -> ChatOutcome:
    return ChatOutcome(
        content=content,
        model=model,
        provider_alias="opponent",
        attempts=attempts,
        request_ids=("req-ok",),
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


def stub_replies(monkeypatch: pytest.MonkeyPatch, replies: list):
    """Each call to chat() pops the next scripted reply; an Exception
    instance is raised instead of returned."""
    calls: list[dict] = []

    def fake_chat(messages, **kwargs):
        calls.append(kwargs)
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(model_turn_module.llm_client, "chat", fake_chat)
    return calls


def test_legal_reply_is_applied_with_full_provenance(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_replies(monkeypatch, [fake_outcome('{"move": "e2e4"}')])

    result = model_turn(conn, workspace["id"])

    assert result.outcome == "model_move"
    assert result.move_result.move["san"] == "e4"
    assert result.move_result.move["actor"] == "model"
    assert result.move_result.move["model"] == "gpt-5.6-luna"
    (attempt,) = result.attempts
    assert attempt["status"] == "applied"
    assert attempt["applied_move_id"] == result.move_result.move["id"]
    assert attempt["raw_response"] == '{"move": "e2e4"}'
    assert attempt["prompt_version"] == "move-v1"
    assert attempt["fen"] == chess.STARTING_FEN


def test_capability_fallback_provenance_is_persisted_not_discarded(tmp_path, monkeypatch):
    """The transport already computes how many HTTP attempts a reply took
    and whether a capability got dropped after the provider rejected it
    (ChatOutcome); this must actually land in the stored attempt, not
    just get thrown away after being calculated."""
    conn, workspace = make_workspace(tmp_path)
    stub_replies(
        monkeypatch,
        [
            fake_outcome(
                '{"move": "e2e4"}',
                attempts=3,
                json_mode_dropped=True,
                reasoning_effort_dropped=True,
            )
        ],
    )

    result = model_turn(conn, workspace["id"])

    (attempt,) = result.attempts
    assert attempt["transport_attempts"] == 3
    assert attempt["json_mode_dropped"] == 1
    assert attempt["reasoning_effort_dropped"] == 1


def test_illegal_then_legal_retains_both_attempts_and_applies_one_move(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_replies(
        monkeypatch,
        [fake_outcome('{"move": "e2e5"}'), fake_outcome('{"move": "d2d4"}')],
    )

    result = model_turn(conn, workspace["id"])

    assert result.outcome == "model_move"
    statuses = [attempt["status"] for attempt in result.attempts]
    assert statuses == ["illegal", "applied"]
    assert result.attempts[0]["is_legal"] == 0
    assert result.attempts[0]["parsed_move"] == "e2e5"
    (count,) = conn.execute("SELECT COUNT(*) FROM moves").fetchone()
    assert count == 1


def test_persistent_illegal_replies_end_in_the_deterministic_fallback(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_replies(
        monkeypatch,
        [fake_outcome('{"move": "e2e5"}'), fake_outcome('{"move": "a1a8"}')],
    )

    result = model_turn(conn, workspace["id"])

    assert result.outcome == "fallback_move"
    # First legal move in UCI sort order from the starting position.
    assert result.move_result.move["uci"] == "a2a3"
    assert result.move_result.move["actor"] == "fallback"
    statuses = [attempt["status"] for attempt in result.attempts]
    assert statuses == ["illegal", "illegal", "applied"]
    assert result.attempts[2]["actor"] == "fallback"
    assert "Fallback played a2a3" in result.detail
    # The board advanced; the game is not waiting on the model.
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"].split(" ")[1] == "b"


def test_unparsable_empty_and_bad_syntax_replies_are_classified(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    monkeypatch.setenv("MODEL_TURN_MAX_ATTEMPTS", "3")
    stub_replies(
        monkeypatch,
        [
            fake_outcome("I would castle early."),
            fake_outcome("   "),
            fake_outcome('{"move": "castle kingside"}'),
        ],
    )

    result = model_turn(conn, workspace["id"])

    assert result.outcome == "fallback_move"
    statuses = [attempt["status"] for attempt in result.attempts]
    assert statuses == ["parse_failed", "empty", "invalid_move_syntax", "applied"]
    assert result.attempts[2]["parsed_move"] == "castle kingside"
    # Raw evidence survives for every reply that arrived.
    assert result.attempts[0]["raw_response"] == "I would castle early."


def test_transport_failure_every_attempt_returns_unavailable_without_moving(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_replies(
        monkeypatch,
        [
            LlmRequestError("502 from opponent", request_ids=("req-1",)),
            LlmRequestError("timeout", request_ids=("req-2", "req-3")),
        ],
    )

    result = model_turn(conn, workspace["id"])

    assert result.outcome == "unavailable"
    assert result.move_result is None
    assert "No move was played" in result.detail
    statuses = [attempt["status"] for attempt in result.attempts]
    assert statuses == ["transport_failed", "transport_failed"]
    assert result.attempts[0]["request_ids_json"] == '["req-1"]'
    assert result.attempts[1]["request_ids_json"] == '["req-2", "req-3"]'
    reloaded = get_workspace(conn, workspace["id"])
    assert reloaded["board_fen"] == chess.STARTING_FEN
    (count,) = conn.execute("SELECT COUNT(*) FROM moves").fetchone()
    assert count == 0


def test_transport_failure_then_reply_recovers(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_replies(
        monkeypatch,
        [LlmRequestError("flaky", request_ids=()), fake_outcome('{"move": "g1f3"}')],
    )

    result = model_turn(conn, workspace["id"])

    assert result.outcome == "model_move"
    statuses = [attempt["status"] for attempt in result.attempts]
    assert statuses == ["transport_failed", "applied"]


def test_failed_attempts_survive_even_when_the_turn_fails(tmp_path, monkeypatch):
    """Attempts commit as they happen: a second connection sees them
    after an unavailable turn."""
    conn, workspace = make_workspace(tmp_path)
    stub_replies(
        monkeypatch,
        [LlmRequestError("down", request_ids=()), LlmRequestError("down", request_ids=())],
    )
    model_turn(conn, workspace["id"])

    other = get_connection(tmp_path / "test.db")
    try:
        (count,) = other.execute("SELECT COUNT(*) FROM model_attempts").fetchone()
        assert count == 2
    finally:
        other.close()


def test_checkmate_by_the_model_ends_the_game_as_a_loss(tmp_path, monkeypatch):
    from euro_chess_studio.actions.games import start_game

    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 300)
    # Fool's mate: the participant opens badly, the model mates.
    make_move(conn, workspace["id"], "f2f3")
    make_move(conn, workspace["id"], "e7e5", actor="model", model="stub")
    make_move(conn, workspace["id"], "g2g4")
    stub_replies(monkeypatch, [fake_outcome('{"move": "d8h4"}')])

    result = model_turn(conn, workspace["id"])

    assert result.outcome == "model_move"
    assert result.move_result.game_result == "loss"


def test_uses_the_games_chosen_opponent_model(tmp_path, monkeypatch):
    from euro_chess_studio.actions.games import start_game

    conn, workspace = make_workspace(tmp_path)
    monkeypatch.setenv("OPPONENT_MODELS", "gemma-4-2b-local")
    calls = stub_replies(monkeypatch, [fake_outcome('{"move": "e7e5"}', model="gemma-4-2b-local")])
    start_game(conn, workspace["id"], 300, opponent_model="gemma-4-2b-local")
    make_move(conn, workspace["id"], "e2e4")

    result = model_turn(conn, workspace["id"])

    assert calls[0]["model"] == "gemma-4-2b-local"
    assert result.move_result.move["model"] == "gemma-4-2b-local"
    assert result.attempts[0]["model"] == "gemma-4-2b-local"


def test_no_legal_moves_raises(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    # Checkmated position: black to move, no legal moves.
    conn.execute(
        "UPDATE workspaces SET board_fen = ? WHERE id = ?",
        ("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3", workspace["id"]),
    )
    conn.commit()
    with pytest.raises(ModelTurnError):
        model_turn(conn, workspace["id"])


def test_max_attempts_is_configurable_and_clamped(monkeypatch):
    monkeypatch.setenv("MODEL_TURN_MAX_ATTEMPTS", "4")
    assert model_turn_module.max_attempts() == 4
    monkeypatch.setenv("MODEL_TURN_MAX_ATTEMPTS", "99")
    assert model_turn_module.max_attempts() == 5
    monkeypatch.setenv("MODEL_TURN_MAX_ATTEMPTS", "0")
    assert model_turn_module.max_attempts() == 1
    monkeypatch.setenv("MODEL_TURN_MAX_ATTEMPTS", "not-a-number")
    assert model_turn_module.max_attempts() == 2


def test_a_stale_reply_is_recorded_explicitly_and_never_misapplied(tmp_path, monkeypatch):
    """Reproduces two overlapping model replies for the same position: the
    first wins the race and applies; the second's reply, decided against
    the same now-stale position, must not be misapplied on top of it even
    though its move happens to still look legal against the stale
    snapshot the second call captured."""
    conn, workspace = make_workspace(tmp_path)
    make_move(conn, workspace["id"], "e2e4")  # black to move
    conn.commit()

    calls = {"count": 0}

    def racing_chat(messages, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            # A second overlapping request reads the same black-to-move
            # position, gets a reply, and applies before this call's
            # reply comes back.
            inner = model_turn(conn, workspace["id"])
            assert inner.outcome == "model_move"
        return fake_outcome('{"move": "e7e5"}')

    monkeypatch.setattr(model_turn_module.llm_client, "chat", racing_chat)

    result = model_turn(conn, workspace["id"])

    assert result.outcome == "stale"
    assert result.move_result is None
    (stale_attempt,) = [a for a in result.attempts if a["status"] == "stale"]
    assert stale_attempt["is_legal"] is None
    assert stale_attempt["parsed_move"] == "e7e5"

    # Exactly one model move landed on the board -- the race's winner.
    # The stale reply was not misapplied on top of it, and no attempt
    # record falsely claims status=applied/is_legal=1 for it.
    moves = conn.execute("SELECT actor, uci, is_legal FROM moves ORDER BY created_at").fetchall()
    model_moves = [m for m in moves if m["actor"] == "model"]
    assert len(model_moves) == 1
    assert model_moves[0]["uci"] == "e7e5"
    assert model_moves[0]["is_legal"] == 1
    applied_attempts = [a for a in result.attempts if a["status"] == "applied"]
    assert applied_attempts == []


def test_a_stale_fallback_is_also_caught(tmp_path, monkeypatch):
    """Both of the outer call's own attempts are garbage, so it would
    normally end in the deterministic fallback -- but a race wins and
    moves the board first, so the fallback must be refused too rather
    than silently applying a move decided against a stale position."""
    conn, workspace = make_workspace(tmp_path)
    make_move(conn, workspace["id"], "e2e4")
    conn.commit()

    state = {"racing": False, "raced": False}

    def racing_chat(messages, **kwargs):
        if state["racing"]:
            # The nested/inner call's own chat invocation.
            return fake_outcome('{"move": "e7e5"}')
        if not state["raced"]:
            state["raced"] = True
            state["racing"] = True
            inner = model_turn(conn, workspace["id"])
            state["racing"] = False
            assert inner.outcome == "model_move"
            return fake_outcome("not json at all")
        return fake_outcome("still not json")

    monkeypatch.setattr(model_turn_module.llm_client, "chat", racing_chat)

    result = model_turn(conn, workspace["id"])

    assert result.outcome == "stale"
    assert result.move_result is None
    (stale_attempt,) = [a for a in result.attempts if a["status"] == "stale"]
    assert stale_attempt["actor"] == "fallback"
    model_moves = [
        m for m in conn.execute("SELECT actor FROM moves").fetchall() if m["actor"] == "model"
    ]
    assert len(model_moves) == 1


def test_deadline_exceeded_stops_retrying_before_a_second_attempt(tmp_path, monkeypatch):
    """Reproduces the reported unbounded-latency risk: without an
    overall deadline, MODEL_TURN_MAX_ATTEMPTS alone let worst-case
    wall-clock time multiply with each attempt's own transport retries.
    The deadline must stop the loop from starting another HTTP round
    trip once time is up, resolving with whatever already happened."""
    conn, workspace = make_workspace(tmp_path)
    monkeypatch.setenv("MODEL_TURN_DEADLINE_SECONDS", "10")
    monkeypatch.setenv("MODEL_TURN_MAX_ATTEMPTS", "5")

    call_log = []

    def fake_chat(*args, **kwargs):
        call_log.append(kwargs.get("timeout"))
        return fake_outcome('{"move": "e2e5"}')  # illegal from the start position

    monkeypatch.setattr(model_turn_module.llm_client, "chat", fake_chat)

    # deadline = 0.0 + 10 = 10.0. First loop check (1.0) is still within
    # budget, so one attempt runs; the second loop check (20.0) is past
    # it, so the loop stops instead of trying a 2nd, 3rd, 4th, 5th time.
    clock = iter([0.0, 1.0, 20.0])
    monkeypatch.setattr(model_turn_module.time, "monotonic", lambda: next(clock))

    result = model_turn(conn, workspace["id"])

    assert len(call_log) == 1
    assert result.outcome == "fallback_move"
    statuses = [attempt["status"] for attempt in result.attempts]
    assert statuses == ["illegal", "applied"]


def test_deadline_exceeded_with_no_replies_reports_unavailable(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    monkeypatch.setenv("MODEL_TURN_DEADLINE_SECONDS", "10")
    monkeypatch.setenv("MODEL_TURN_MAX_ATTEMPTS", "5")
    stub_replies(monkeypatch, [LlmRequestError("down", request_ids=())])

    clock = iter([0.0, 1.0, 20.0])
    monkeypatch.setattr(model_turn_module.time, "monotonic", lambda: next(clock))

    result = model_turn(conn, workspace["id"])

    assert result.outcome == "unavailable"
    assert "did not reply within 10s" in result.detail
    statuses = [attempt["status"] for attempt in result.attempts]
    assert statuses == ["transport_failed"]


def test_the_last_attempts_timeout_is_capped_by_the_remaining_deadline(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    monkeypatch.setenv("MODEL_TURN_DEADLINE_SECONDS", "10")

    seen_timeouts = []

    def fake_chat(*args, **kwargs):
        seen_timeouts.append(kwargs["timeout"])
        return fake_outcome('{"move": "e2e4"}')

    monkeypatch.setattr(model_turn_module.llm_client, "chat", fake_chat)
    # deadline = 0.0 + 10 = 10.0; the loop's only check sees 3s left.
    clock = iter([0.0, 7.0])
    monkeypatch.setattr(model_turn_module.time, "monotonic", lambda: next(clock))

    model_turn(conn, workspace["id"])

    assert seen_timeouts == [3.0]


def test_clock_expiry_after_a_legitimate_reply_still_records_the_attempt(tmp_path, monkeypatch):
    """Reproduces the reported data loss: a reply that arrives after the
    game's clock ran out used to vanish with zero persisted attempts,
    because make_move's clock check raised before model_turn ever
    recorded anything for it."""
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 60)
    stub_replies(monkeypatch, [fake_outcome('{"move": "e2e4"}')])

    # Backdate the game so make_move's clock check reads it as already
    # expired, simulating a reply that arrived too late.
    conn.execute(
        "UPDATE games SET started_at = '2000-01-01T00:00:00+00:00' WHERE workspace_id = ?",
        (workspace["id"],),
    )
    conn.commit()

    with pytest.raises(GameClockExpiredError):
        model_turn(conn, workspace["id"])

    (attempt,) = conn.execute("SELECT * FROM model_attempts").fetchall()
    assert attempt["status"] == "clock_expired"
    assert attempt["parsed_move"] == "e2e4"
    assert attempt["raw_response"] == '{"move": "e2e4"}'
    assert attempt["is_legal"] is None
    # The reply was never applied to the board.
    assert conn.execute("SELECT COUNT(*) FROM moves").fetchone()[0] == 0
    # The clock check itself already recorded the timeout loss.
    game = conn.execute("SELECT * FROM games WHERE workspace_id = ?", (workspace["id"],)).fetchone()
    assert game["result"] == "loss_timeout"


def test_clock_expiry_during_the_fallback_also_records_the_attempt(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    start_game(conn, workspace["id"], 60)
    stub_replies(monkeypatch, [fake_outcome("not json"), fake_outcome("still not json")])

    conn.execute(
        "UPDATE games SET started_at = '2000-01-01T00:00:00+00:00' WHERE workspace_id = ?",
        (workspace["id"],),
    )
    conn.commit()

    with pytest.raises(GameClockExpiredError):
        model_turn(conn, workspace["id"])

    statuses = [
        row["status"] for row in conn.execute("SELECT status FROM model_attempts").fetchall()
    ]
    assert statuses == ["parse_failed", "parse_failed", "clock_expired"]
    assert conn.execute("SELECT COUNT(*) FROM moves").fetchone()[0] == 0


def test_attempts_are_queryable_by_scope(tmp_path, monkeypatch):
    conn, workspace = make_workspace(tmp_path)
    stub_replies(
        monkeypatch,
        [fake_outcome('{"move": "e2e5"}'), fake_outcome('{"move": "e2e4"}')],
    )
    model_turn(conn, workspace["id"])

    move_attempts = list_attempts(conn, workspace_id=workspace["id"], task="move", actor="model")
    assert len(move_attempts) == 2
    assert list_attempts(conn, task="scenario") == []
