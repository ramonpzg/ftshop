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
    "You map chess games to concrete real-world situations for a fine-tuning workshop. "
    "Be direct and specific. Return JSON only. The assessment is terse. The real-world "
    "description explains the relationship to the game in three to five sentences. The "
    "video prompt is one flowing paragraph of four to eight sentences in present tense. "
    "It depicts only the real-world situation, never a chessboard, chess pieces, chess "
    "notation, or a chess move. Establish one shot and setting, define the people through "
    "visible details, describe one clear sequence of physical actions, specify camera "
    "movement, lighting, and sound. Do not request readable text or logos. Describe visible "
    "behaviour instead of internal emotions."
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
        "Assess the game, explain a concrete real-world situation with the same tension "
        "or trade-off, then turn that situation into a detailed prompt for a short video. "
        "The video must show the real-world situation rather than a literal chess scene.\n"
        'Respond with JSON: {"assessment": "...", "real_world": "...", '
        '"video_prompt": "..."}'
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
    """The assessment, real-world mapping, and video prompt, or None."""
    parsed = _extract_json(text)
    if parsed is None:
        return None
    assessment = parsed.get("assessment")
    real_world = parsed.get("real_world")
    video_prompt = parsed.get("video_prompt")
    if not isinstance(assessment, str) or not assessment.strip():
        return None
    if not isinstance(real_world, str) or not real_world.strip():
        return None
    if not isinstance(video_prompt, str) or not video_prompt.strip():
        return None
    return {
        "assessment": assessment.strip(),
        "real_world": real_world.strip(),
        "video_prompt": video_prompt.strip(),
    }
