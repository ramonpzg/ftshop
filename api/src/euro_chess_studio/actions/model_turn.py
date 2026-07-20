"""Action: the model's turn, as an explicit state machine.

Each request to the model is one recorded attempt: transport failure,
empty reply, unparsable reply, syntactically invalid move, illegal
move, a stale reply, or an applied move. Failed attempts commit
immediately so the eval can count them even when the turn ultimately
fails. After the configurable attempt limit:

- If the model answered at least once (garbage or illegal), the turn
  ends with a deterministic fallback: the first legal move in UCI sort
  order, recorded with actor 'fallback' so it never counts as model
  skill. The game continues; the board is never stuck.
- If every attempt died in transport, no move is invented. The turn
  returns 'unavailable' with the reason, and the client offers a retry.
  That is loud waiting, not silent sticking.

Every reply the model produces was judged against the position snapshot
taken before the network call. If the board changes while that call is
in flight (a concurrent request wins the race, a clock expiry starts a
fresh game), applying the reply to whatever board exists later would
misrepresent a decision made against stale information as a legitimate
answer to the current position -- and could even coincidentally look
legal on the new board. make_move's MovePrecondition catches this: a
mismatch raises StaleMoveError, the attempt is recorded as 'stale'
rather than mislabeled 'applied', and the turn ends with outcome
'stale' instead of guessing.

Two more failure modes get the same "record the evidence, never lose
it silently" treatment:

- The whole turn (however many attempts MODEL_TURN_MAX_ATTEMPTS allows)
  is bounded by one overall MODEL_TURN_DEADLINE_SECONDS deadline, not
  just by attempt count. Attempt count alone let worst-case latency
  multiply unpredictably: each attempt could itself retry the HTTP call
  up to three times at MODEL_MOVE_TIMEOUT_SECONDS each, so two
  model-turn attempts could in principle take several minutes -- longer
  than the shortest allowed game. The deadline caps total wall-clock
  time regardless of how retries stack, and the last attempt's own
  timeout is shortened to whatever time remains -- but that only holds
  if llm_client honours it as a real budget rather than a per-attempt
  number to reuse. llm_client._chat_completion turns the timeout it is
  given into its own absolute deadline and re-checks the time left
  before every one of its internal HTTP attempts and backoff sleeps, so
  a short remaining allowance here stays short all the way down to the
  socket, instead of being handed to up to three retries as if each
  got a fresh clock.
- If the game's clock expires between receiving a legitimate reply and
  applying it (make_move's own clock check raises GameClockExpiredError
  first), that attempt is recorded before the exception propagates,
  instead of the model's answer -- possibly a correct one -- vanishing
  with no trace because the clock happened to run out in between.

MODEL_TURN_MAX_ATTEMPTS configures the retry limit (default 2, clamped
1-5). MODEL_TURN_DEADLINE_SECONDS configures the overall deadline
(default 30, clamped 5-120): comfortably under the 60s minimum game
time limit, so even the shortest match leaves most of its clock after
one model turn.
"""

import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from euro_chess_studio.actions.errors import (
    GameClockExpiredError,
    NotYourTurnError,
    StaleMoveError,
    WorkspaceNotFoundError,
)
from euro_chess_studio.actions.moves import (
    PARTICIPANT_COLOR,
    MakeMoveResult,
    MovePrecondition,
    make_move,
)
from euro_chess_studio.calculations.llm_prompts import (
    MOVE_PROMPT_VERSION,
    analyze_move_reply,
    build_move_messages,
)
from euro_chess_studio.chess.board import get_legal_moves
from euro_chess_studio.data import llm_client
from euro_chess_studio.data.games_repo import get_active_game
from euro_chess_studio.data.model_attempts_repo import insert_attempt
from euro_chess_studio.data.moves_repo import list_legal_sans
from euro_chess_studio.data.workspaces_repo import get_workspace

# A move reply should be fast; the game clock keeps running while the
# model thinks, so waiting the transport's full two minutes would eat
# the participant's game. Documented operation-specific timeout, used
# as the ceiling for any one HTTP attempt -- the overall turn is
# additionally bounded by MODEL_TURN_DEADLINE_SECONDS below.
MODEL_MOVE_TIMEOUT_SECONDS = 60.0

DEFAULT_MAX_ATTEMPTS = 2
DEFAULT_DEADLINE_SECONDS = 30.0


class ModelTurnError(RuntimeError):
    """The turn could not even start (no legal moves in the position)."""


@dataclass(frozen=True)
class ModelTurnResult:
    # "model_move": an attempt was applied. "fallback_move": the model
    # kept failing and the deterministic fallback moved. "unavailable":
    # transport never delivered a reply; nothing moved. "stale": the
    # position changed while a reply was in flight; nothing moved.
    outcome: str
    move_result: MakeMoveResult | None
    attempts: list[sqlite3.Row]
    detail: str | None


def max_attempts() -> int:
    raw = os.environ.get("MODEL_TURN_MAX_ATTEMPTS", "")
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_ATTEMPTS
    return max(1, min(5, value))


def deadline_seconds() -> float:
    raw = os.environ.get("MODEL_TURN_DEADLINE_SECONDS", "")
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_DEADLINE_SECONDS
    return max(5.0, min(120.0, value))


def model_turn(conn: sqlite3.Connection, workspace_id: str) -> ModelTurnResult:
    workspace = get_workspace(conn, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError(f"unknown workspace id: {workspace_id}")

    fen = workspace["board_fen"]
    legal_moves = get_legal_moves(fen)
    if not legal_moves:
        raise ModelTurnError("no legal moves in this position; the game is over")

    # A timed match may have picked its own opponent; None falls back
    # to OPENAI_MODEL. Small Gemma and a frontier model on the same
    # board is the whole "different results" demo.
    active = get_active_game(conn, workspace_id)
    game_id = active["id"] if active is not None else None

    # Symmetric with make_move's own turn-ownership check: a raw
    # /model-move call (or a UI that let the model be triggered on the
    # participant's turn) must not spend an LLM call, let alone a move,
    # on White's turn. This is a courtesy early exit against the state
    # this call read; make_move's check inside its write lock is what
    # actually holds under a concurrent race, same as the participant
    # side.
    if game_id is not None and fen.split(" ")[1] == PARTICIPANT_COLOR:
        raise NotYourTurnError("it is the participant's turn; the model cannot move for them")

    opponent_model = active["opponent_model"] if active is not None else None
    requested_model = opponent_model or llm_client.get_llm_model()
    ply = len(list_legal_sans(conn, workspace_id, game_id))
    messages = build_move_messages(fen, legal_moves)
    # Captured once, applied to every attempt in this turn: if the board
    # moves out from under a reply, make_move refuses to apply it.
    precondition = MovePrecondition(fen=fen, game_id=game_id, ply=ply)

    attempts: list[sqlite3.Row] = []
    limit = max_attempts()
    deadline = time.monotonic() + deadline_seconds()
    deadline_exceeded = False

    def record(attempt_number: int, *, actor: str = "model", **fields) -> sqlite3.Row:
        row = insert_attempt(
            conn,
            workspace_id=workspace_id,
            game_id=game_id,
            task="move",
            actor=actor,
            model=fields.pop("model", requested_model),
            provider_alias=fields.pop("provider_alias", "opponent"),
            prompt_version=MOVE_PROMPT_VERSION,
            ply=ply,
            fen=fen,
            attempt_number=attempt_number,
            json_requested=True,
            **fields,
        )
        attempts.append(row)
        return row

    replies_received = 0
    for attempt_number in range(1, limit + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            # The overall turn deadline is up: stop asking, resolve with
            # whatever attempts already happened rather than starting
            # another HTTP round trip that would only push latency
            # further past what a short game clock can afford.
            deadline_exceeded = True
            break
        try:
            reply = llm_client.chat(
                messages,
                json_response=True,
                # The last attempt before the deadline is capped to
                # whatever time remains, so a single slow call cannot by
                # itself blow past the overall turn budget.
                timeout=min(MODEL_MOVE_TIMEOUT_SECONDS, remaining),
                model=opponent_model,
            )
        except llm_client.LlmRequestError as exc:
            record(
                attempt_number,
                status="transport_failed",
                error_detail=str(exc)[:400],
                request_ids=exc.request_ids,
            )
            conn.commit()
            continue

        replies_received += 1
        shared: dict[str, Any] = {
            "model": reply.model,
            "provider_alias": reply.provider_alias,
            "raw_response": reply.content,
            "request_ids": reply.request_ids,
            "transport_attempts": reply.attempts,
            "json_mode_dropped": reply.json_mode_dropped,
            "reasoning_effort_dropped": reply.reasoning_effort_dropped,
        }
        if not reply.content.strip():
            record(attempt_number, status="empty", **shared)
            conn.commit()
            continue

        analysis = analyze_move_reply(reply.content)
        if analysis.uci is None:
            record(
                attempt_number,
                status="invalid_move_syntax" if analysis.parse_ok else "parse_failed",
                parse_ok=analysis.parse_ok,
                parsed_move=analysis.move_text,
                **shared,
            )
            conn.commit()
            continue

        if analysis.uci not in legal_moves:
            record(
                attempt_number,
                status="illegal",
                parse_ok=True,
                parsed_move=analysis.uci,
                is_legal=False,
                **shared,
            )
            conn.commit()
            continue

        # The applied move and its attempt record commit together. The
        # precondition guards against a slow reply landing after the
        # board moved on (a concurrent request, a fresh game): a
        # mismatch raises instead of silently applying a decision made
        # against a position that no longer exists.
        try:
            move_result = make_move(
                conn,
                workspace_id,
                analysis.uci,
                actor="model",
                model=reply.model,
                commit=False,
                precondition=precondition,
            )
        except GameClockExpiredError as exc:
            # The reply arrived -- possibly a perfectly good one -- but
            # the clock ran out before it could be applied. Record it
            # before the exception propagates so this evidence is never
            # just lost; is_legal is left unset because the board was
            # never actually checked against it.
            record(
                attempt_number,
                status="clock_expired",
                parse_ok=True,
                parsed_move=analysis.uci,
                error_detail=str(exc)[:400],
                **shared,
            )
            conn.commit()
            raise
        except StaleMoveError as exc:
            record(
                attempt_number,
                status="stale",
                parse_ok=True,
                parsed_move=analysis.uci,
                error_detail=str(exc)[:400],
                **shared,
            )
            conn.commit()
            return ModelTurnResult(
                outcome="stale",
                move_result=None,
                attempts=attempts,
                detail=(
                    "The position changed before this reply could be applied. "
                    "Refresh and try again."
                ),
            )
        # The precondition guarantees the board matched exactly what
        # legal_moves was computed from, so this is provably legal; the
        # attempt still records the actual outcome rather than assuming.
        record(
            attempt_number,
            status="applied",
            parse_ok=True,
            parsed_move=analysis.uci,
            is_legal=bool(move_result.move["is_legal"]),
            applied_move_id=move_result.move["id"],
            **shared,
        )
        conn.commit()
        return ModelTurnResult(
            outcome="model_move", move_result=move_result, attempts=attempts, detail=None
        )

    if replies_received == 0:
        if deadline_exceeded:
            detail = (
                f"{requested_model} did not reply within {deadline_seconds():.0f}s. "
                "No move was played."
            )
        else:
            detail = (
                f"{requested_model} could not be reached after {limit} "
                f"attempt{'s' if limit != 1 else ''}. No move was played."
            )
        return ModelTurnResult(
            outcome="unavailable", move_result=None, attempts=attempts, detail=detail
        )

    # The model answered but never produced a legal move. The documented
    # workshop outcome: the first legal move in UCI sort order, recorded
    # as the fallback's move, not the model's. None of the intermediate
    # attempts touched the board, so the precondition should still hold;
    # if something else moved concurrently, it is caught the same way.
    fallback_uci = sorted(legal_moves)[0]
    try:
        move_result = make_move(
            conn,
            workspace_id,
            fallback_uci,
            actor="fallback",
            model=requested_model,
            commit=False,
            precondition=precondition,
        )
    except GameClockExpiredError as exc:
        record(
            limit + 1,
            actor="fallback",
            status="clock_expired",
            parse_ok=True,
            parsed_move=fallback_uci,
            error_detail=str(exc)[:400],
        )
        conn.commit()
        raise
    except StaleMoveError as exc:
        record(
            limit + 1,
            actor="fallback",
            status="stale",
            parse_ok=True,
            parsed_move=fallback_uci,
            error_detail=str(exc)[:400],
        )
        conn.commit()
        return ModelTurnResult(
            outcome="stale",
            move_result=None,
            attempts=attempts,
            detail=(
                "The position changed before the fallback could be applied. Refresh and try again."
            ),
        )
    record(
        limit + 1,
        actor="fallback",
        status="applied",
        parse_ok=True,
        parsed_move=fallback_uci,
        is_legal=bool(move_result.move["is_legal"]),
        applied_move_id=move_result.move["id"],
        error_detail=f"deterministic fallback after {limit} failed model attempts",
    )
    conn.commit()
    return ModelTurnResult(
        outcome="fallback_move",
        move_result=move_result,
        attempts=attempts,
        detail=(
            f"{requested_model} did not produce a legal move in {limit} "
            f"attempt{'s' if limit != 1 else ''}. "
            f"Fallback played {fallback_uci} (first legal move in UCI order)."
        ),
    )
