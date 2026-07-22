"""Pure reply parsing and validation. The model never touches board
state; this module only decides what a raw reply claimed and whether
that claim names a listed legal move."""

import json
import re
from dataclasses import dataclass
from typing import Literal

_UCI_SHAPE = re.compile(r"^[a-h][1-8][a-h][1-8][nbrq]?$")

ReplyStatus = Literal["ok", "malformed_json", "wrong_shape", "illegal"]


@dataclass(frozen=True)
class ReplyVerdict:
    status: ReplyStatus
    move: str | None = None
    comment: str | None = None
    reason: str = ""


def extract_json_object(text: str) -> dict | None:
    """Copied from the backend's llm_prompts.extract_json_object so the
    phone TUI never imports the workshop app: fenced block first, then
    the widest brace span. Code-fence tolerance is deliberate and
    tested; a fence is a contract violation the corrective request does
    not need to be spent on."""
    candidate = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", candidate, re.DOTALL)
        if brace:
            candidate = brace.group(0)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def judge_move_reply(raw: str, legal_uci: set[str]) -> ReplyVerdict:
    """Shape first, membership second. Extra keys are tolerated: the
    schema forbids them server-side, and rejecting a legal move over a
    stray key would fail a turn for nothing."""
    if not raw.strip():
        return ReplyVerdict("malformed_json", reason="the reply was empty")
    parsed = extract_json_object(raw)
    if parsed is None:
        return ReplyVerdict("malformed_json", reason="the reply was not one JSON object")
    move = parsed.get("move")
    if not isinstance(move, str) or not move.strip():
        return ReplyVerdict("wrong_shape", reason='the JSON object had no string "move"')
    comment = parsed.get("comment")
    if not isinstance(comment, str):
        return ReplyVerdict("wrong_shape", reason='the JSON object had no string "comment"')
    move = move.strip().lower()
    if not _UCI_SHAPE.match(move) or move not in legal_uci:
        return ReplyVerdict(
            "illegal",
            move=move,
            reason=f'move "{move}" is not in LEGAL_MOVES',
        )
    return ReplyVerdict("ok", move=move, comment=" ".join(comment.split()))
