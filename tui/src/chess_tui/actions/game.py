"""Game orchestration. Actions compose calculations and repositories
and own every transaction. python-chess is the sole authority on
rules; the model only ever picks from the legal list and its reply is
validated again here regardless of the server-side grammar.

Sides are assigned per game (the app flips a coin); the participant's
color is persisted with the game and the model plays the other side,
moving first when it has White.

Failure policy, from the phase prompt: a malformed or illegal reply
gets exactly one corrective request naming the rejection; if that also
fails, nothing moves and the participant chooses retry or quit. A
transport failure likewise leaves the board unchanged. No silent
fallback move is ever attributed to the model."""

import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

import chess

from chess_tui.calculations.moves import ParsedMove, legal_moves_uci_san, san_history_text
from chess_tui.calculations.prompt import (
    MOVE_PROMPT_VERSION,
    build_corrective_message,
    build_messages,
    build_move_grammar,
    build_user_message,
    system_prompt,
)
from chess_tui.calculations.replies import judge_move_reply
from chess_tui.data import attempts_repo, games_repo, plies_repo
from chess_tui.data.llm_client import LlmClient, TransportFailure

_TERMINATIONS = {
    chess.Termination.CHECKMATE: "checkmate",
    chess.Termination.STALEMATE: "stalemate",
    chess.Termination.INSUFFICIENT_MATERIAL: "insufficient material",
    chess.Termination.SEVENTYFIVE_MOVES: "seventyfive moves",
    chess.Termination.FIVEFOLD_REPETITION: "fivefold repetition",
}

FailureCode = Literal["invalid_reply", "unreachable", "timeout", "http_error", "canceled"]


@dataclass
class GameState:
    game_id: str
    board: chess.Board
    model: str
    player_name: str
    participant_color: chess.Color
    started_monotonic: float
    over: bool = False
    result: str | None = None
    termination: str | None = None
    last_comment: str | None = None
    pending_failure: "TurnFailure | None" = None
    sans: list[str] = field(default_factory=list)

    @property
    def model_color(self) -> chess.Color:
        return not self.participant_color

    @property
    def participant_color_name(self) -> str:
        return "White" if self.participant_color == chess.WHITE else "Black"

    @property
    def model_color_name(self) -> str:
        return "White" if self.model_color == chess.WHITE else "Black"

    @property
    def model_to_move(self) -> bool:
        return not self.over and self.board.turn == self.model_color


@dataclass(frozen=True)
class TurnFailure:
    code: FailureCode
    detail: str


@dataclass(frozen=True)
class AppliedMove:
    uci: str
    san: str
    comment: str | None
    game_over: bool


def start_game(
    conn: sqlite3.Connection,
    model: str,
    participant_color: chess.Color,
    player_name: str,
) -> GameState:
    state = GameState(
        game_id=uuid.uuid4().hex[:12],
        board=chess.Board(),
        model=model,
        player_name=player_name,
        participant_color=participant_color,
        started_monotonic=time.monotonic(),
    )
    games_repo.insert_game(
        conn,
        state.game_id,
        _now(),
        model,
        MOVE_PROMPT_VERSION,
        "white" if participant_color == chess.WHITE else "black",
        player_name,
    )
    conn.commit()
    return state


def apply_participant_move(
    conn: sqlite3.Connection, state: GameState, parsed: ParsedMove
) -> AppliedMove:
    """The move is already legal by construction (parse_participant_move
    checked it against this position). Persisted and committed before
    any network call happens."""
    applied = _apply_move(conn, state, parsed.uci, parsed.san, "participant", None)
    conn.commit()
    return applied


def play_model_turn(
    conn: sqlite3.Connection, state: GameState, client: LlmClient
) -> AppliedMove | TurnFailure:
    """One initial request, at most one corrective request. Every raw
    reply and every transport failure is persisted as an immutable
    attempt row; failed attempts commit as they happen so evidence
    survives a failed turn. On failure the board is left unchanged and
    retry repeats the turn."""
    if not state.model_to_move:
        raise ValueError("not the model's turn")
    state.pending_failure = None
    fen = state.board.fen()
    ply = len(state.board.move_stack) + 1
    legal = legal_moves_uci_san(fen)
    legal_set = {uci for uci, _ in legal}
    grammar = build_move_grammar([uci for uci, _ in legal])
    system = system_prompt(state.model_color_name)
    opponent_last = state.board.peek().uci() if state.board.move_stack else None
    user = build_user_message(
        fen,
        san_history_text(state.sans),
        opponent_last,
        state.sans[-1] if state.sans else None,
        legal,
    )

    judged = _one_request(
        conn, state, client, ply, legal_set, grammar, build_messages(system, user), False
    )
    if isinstance(judged, TurnFailure):
        state.pending_failure = judged
        return judged
    if judged.status != "ok":
        corrective = build_corrective_message(user, judged.raw, judged.reason)
        judged = _one_request(
            conn,
            state,
            client,
            ply,
            legal_set,
            grammar,
            build_messages(system, corrective),
            True,
        )
        if isinstance(judged, TurnFailure):
            state.pending_failure = judged
            return judged
        if judged.status != "ok":
            failure = TurnFailure("invalid_reply", judged.reason)
            state.pending_failure = failure
            return failure

    move_uci = judged.move or ""
    san = state.board.san(chess.Move.from_uci(move_uci))
    applied = _apply_move(conn, state, move_uci, san, "model", judged.comment)
    attempts_repo.insert_attempt(
        conn,
        state.game_id,
        ply,
        judged.attempt,
        judged.corrective,
        "applied",
        judged.raw,
        move_uci,
        judged.comment,
        judged.request_id,
        judged.latency_ms,
        None,
        _now(),
    )
    conn.commit()
    state.last_comment = judged.comment
    return applied


@dataclass(frozen=True)
class _JudgedReply:
    status: str
    attempt: int
    corrective: bool
    raw: str
    reason: str
    move: str | None = None
    comment: str | None = None
    request_id: str | None = None
    latency_ms: int | None = None


def _one_request(
    conn: sqlite3.Connection,
    state: GameState,
    client: LlmClient,
    ply: int,
    legal_set: set[str],
    grammar: str,
    messages: list[dict],
    corrective: bool,
) -> _JudgedReply | TurnFailure:
    attempt = attempts_repo.next_attempt_number(conn, state.game_id, ply)
    try:
        reply = client.request_move(messages, grammar)
    except TransportFailure as failure:
        status = "timeout" if failure.kind == "timeout" else "transport_failed"
        _record_attempt(
            conn,
            state,
            ply,
            attempt,
            corrective,
            status,
            raw_reply=None,
            parsed_move=None,
            detail=failure.detail,
            request_id=failure.request_id,
            latency_ms=failure.latency_ms,
        )
        return TurnFailure(failure.kind, failure.detail)
    except KeyboardInterrupt:
        _record_attempt(
            conn,
            state,
            ply,
            attempt,
            corrective,
            "canceled",
            raw_reply=None,
            parsed_move=None,
            detail="interrupted at the keyboard",
            request_id=None,
            latency_ms=None,
        )
        return TurnFailure("canceled", "model call interrupted")

    verdict = judge_move_reply(reply.content, legal_set)
    if verdict.status != "ok":
        _record_attempt(
            conn,
            state,
            ply,
            attempt,
            corrective,
            verdict.status,
            raw_reply=reply.content,
            parsed_move=verdict.move,
            detail=verdict.reason,
            request_id=reply.request_id,
            latency_ms=reply.latency_ms,
        )
    return _JudgedReply(
        status=verdict.status,
        attempt=attempt,
        corrective=corrective,
        raw=reply.content,
        reason=verdict.reason,
        move=verdict.move,
        comment=verdict.comment,
        request_id=reply.request_id,
        latency_ms=reply.latency_ms,
    )


def _record_attempt(
    conn: sqlite3.Connection,
    state: GameState,
    ply: int,
    attempt: int,
    corrective: bool,
    status: str,
    raw_reply: str | None,
    parsed_move: str | None,
    detail: str,
    request_id: str | None,
    latency_ms: int | None,
) -> None:
    """Failed attempts commit individually as they happen: a failed
    reply is evidence that must survive the turn failing."""
    attempts_repo.insert_attempt(
        conn,
        state.game_id,
        ply,
        attempt,
        corrective,
        status,
        raw_reply,
        parsed_move,
        None,
        request_id,
        latency_ms,
        detail,
        _now(),
    )
    conn.commit()


def _apply_move(
    conn: sqlite3.Connection,
    state: GameState,
    uci: str,
    san: str,
    actor: str,
    comment: str | None,
) -> AppliedMove:
    move = chess.Move.from_uci(uci)
    ply = len(state.board.move_stack) + 1
    fen_before = state.board.fen()
    is_capture = state.board.is_capture(move)
    state.board.push(move)
    plies_repo.insert_ply(
        conn,
        state.game_id,
        ply,
        actor,
        uci,
        san,
        fen_before,
        state.board.fen(),
        is_capture,
        comment,
        _now(),
    )
    state.sans.append(san)
    outcome = state.board.outcome()
    if outcome is not None:
        state.over = True
        state.result = outcome.result()
        state.termination = _TERMINATIONS.get(outcome.termination, outcome.termination.name.lower())
        games_repo.finish_game(
            conn,
            state.game_id,
            _now(),
            state.result,
            state.termination,
            round(time.monotonic() - state.started_monotonic, 1),
        )
    return AppliedMove(uci=uci, san=san, comment=comment, game_over=state.over)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
