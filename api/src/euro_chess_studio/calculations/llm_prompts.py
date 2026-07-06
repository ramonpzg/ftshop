"""Pure prompt construction and reply parsing for the LLM opponent and
the live game analysis. No I/O here, so every branch is unit-testable
without a network."""

import json
import re

MOVE_SYSTEM_PROMPT = (
    "You are a chess engine assistant playing a casual but competent game. "
    "You always answer with JSON only."
)

ASSESS_SYSTEM_PROMPT = (
    "You are a chess commentator for a fine-tuning workshop. Terse, direct, "
    "no fluff. You relate each position to an everyday real-world scenario "
    "(work, home, sports) in one or two sentences. You always answer with "
    "JSON only."
)


def build_move_messages(fen: str, legal_moves: list[str]) -> list[dict]:
    user = (
        f"Position (FEN): {fen}\n"
        f"Legal moves (UCI): {', '.join(legal_moves)}\n\n"
        "Pick one move from the legal moves list.\n"
        'Respond with JSON: {"move": "<uci>"}'
    )
    return [
        {"role": "system", "content": MOVE_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def build_assess_messages(san_history: list[str], fen: str) -> list[dict]:
    moves_text = " ".join(san_history) if san_history else "(no moves yet)"
    user = (
        f"Moves so far (SAN): {moves_text}\n"
        f"Current position (FEN): {fen}\n\n"
        "Assess the position in one or two short sentences, then map the "
        "state of this game to a concrete everyday scenario.\n"
        'Respond with JSON: {"assessment": "...", "real_world": "..."}'
    )
    return [
        {"role": "system", "content": ASSESS_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _extract_json(text: str) -> dict | None:
    """Parses a JSON object out of a model reply, tolerating code fences
    and surrounding prose."""
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


def parse_move_reply(text: str) -> str | None:
    """The model's chosen UCI move, or None when the reply is unusable.
    Legality is the caller's job; format is ours."""
    parsed = _extract_json(text)
    if parsed is None:
        return None
    move = parsed.get("move")
    if not isinstance(move, str):
        return None
    move = move.strip().lower()
    return move if re.fullmatch(r"[a-h][1-8][a-h][1-8][qrbn]?", move) else None


def parse_assess_reply(text: str) -> dict | None:
    """{"assessment", "real_world"} strings, or None when unusable."""
    parsed = _extract_json(text)
    if parsed is None:
        return None
    assessment = parsed.get("assessment")
    real_world = parsed.get("real_world")
    if not isinstance(assessment, str) or not assessment.strip():
        return None
    return {
        "assessment": assessment.strip(),
        "real_world": real_world.strip() if isinstance(real_world, str) else "",
    }
