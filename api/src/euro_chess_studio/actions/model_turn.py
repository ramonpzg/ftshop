"""Action: the model's turn, as an explicit state machine.

Each request to the model is one recorded attempt: transport failure,
empty reply, unparsable reply, syntactically invalid move, illegal
move, or an applied move. Failed attempts commit immediately so the
eval can count them even when the turn ultimately fails. After the
configurable attempt limit:

- If the model answered at least once (garbage or illegal), the turn
  ends with a deterministic fallback: the first legal move in UCI sort
  order, recorded with actor 'fallback' so it never counts as model
  skill. The game continues; the board is never stuck.
- If every attempt died in transport, no move is invented. The turn
  returns 'unavailable' with the reason, and the client offers a retry.
  That is loud waiting, not silent sticking.

MODEL_TURN_MAX_ATTEMPTS configures the limit (default 2, clamped 1-5).
"""

import os
import sqlite3
from dataclasses import dataclass
from typing import Any

from euro_chess_studio.actions.errors import WorkspaceNotFoundError
from euro_chess_studio.actions.moves import MakeMoveResult, make_move
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
# the participant's game. Documented operation-specific timeout.
MODEL_MOVE_TIMEOUT_SECONDS = 60.0

DEFAULT_MAX_ATTEMPTS = 2


class ModelTurnError(RuntimeError):
    """The turn could not even start (no legal moves in the position)."""


@dataclass(frozen=True)
class ModelTurnResult:
    # "model_move": an attempt was applied. "fallback_move": the model
    # kept failing and the deterministic fallback moved. "unavailable":
    # transport never delivered a reply; nothing moved.
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
    opponent_model = active["opponent_model"] if active is not None else None
    requested_model = opponent_model or llm_client.get_llm_model()
    ply = len(list_legal_sans(conn, workspace_id, game_id))
    messages = build_move_messages(fen, legal_moves)

    attempts: list[sqlite3.Row] = []
    limit = max_attempts()

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
        try:
            reply = llm_client.chat(
                messages,
                json_response=True,
                timeout=MODEL_MOVE_TIMEOUT_SECONDS,
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

        # The applied move and its attempt record commit together.
        move_result = make_move(
            conn, workspace_id, analysis.uci, actor="model", model=reply.model, commit=False
        )
        record(
            attempt_number,
            status="applied",
            parse_ok=True,
            parsed_move=analysis.uci,
            is_legal=True,
            applied_move_id=move_result.move["id"],
            **shared,
        )
        conn.commit()
        return ModelTurnResult(
            outcome="model_move", move_result=move_result, attempts=attempts, detail=None
        )

    if replies_received == 0:
        return ModelTurnResult(
            outcome="unavailable",
            move_result=None,
            attempts=attempts,
            detail=(
                f"{requested_model} could not be reached after {limit} "
                f"attempt{'s' if limit != 1 else ''}. No move was played."
            ),
        )

    # The model answered but never produced a legal move. The documented
    # workshop outcome: the first legal move in UCI sort order, recorded
    # as the fallback's move, not the model's.
    fallback_uci = sorted(legal_moves)[0]
    move_result = make_move(
        conn, workspace_id, fallback_uci, actor="fallback", model=requested_model, commit=False
    )
    record(
        limit + 1,
        actor="fallback",
        status="applied",
        parse_ok=True,
        parsed_move=fallback_uci,
        is_legal=True,
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
