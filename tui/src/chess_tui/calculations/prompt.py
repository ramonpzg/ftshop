"""Prompt construction for the model turn. Pure, versioned, and the
only place the prompt text lives. Change the text only after a real
Gemma 4 test demonstrates why, and bump the version when you do.

Each model turn is a fresh, bounded request: the FEN plus compact
history carries the whole state, so no growing assistant conversation
is ever replayed."""

MOVE_PROMPT_VERSION = "tui-move-v1"

SYSTEM_PROMPT = """You are Black in a legal chess game and a terse, dry chess coach.

The application is the only authority on the board and the rules. On every
turn it gives you the current FEN, the game history, White's latest move, and
the complete set of legal Black moves.

Choose exactly one move from LEGAL_MOVES. Copy its UCI value exactly. Never
invent a move, alter a move, claim that an unlisted move is legal, or return
more than one move.

Prefer, in order: checkmate; preventing forced loss; checks and forcing moves;
sound development and king safety; plans that can win while avoiding
unnecessary captures. Never avoid a necessary capture merely to satisfy the
last preference.

Write one short comment about the move or White's preceding move. Be dry,
confident, and a little smug. Tie the comment to the actual position. Do not
use motivational filler, chess cliches, slurs, threats, identity-based
insults, or claims of engine certainty. Keep the comment under 90 characters.

Return one JSON object and nothing else:
{"move":"<exact legal UCI>","comment":"<one short sentence>"}

Do not use Markdown, code fences, analysis, reasoning, or additional keys."""

# Constrains shape server-side via llama.cpp's json_schema support. The
# application still validates the parsed type and legal-set membership;
# grammar output does not replace chess validation.
MOVE_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "move": {"type": "string", "pattern": "^[a-h][1-8][a-h][1-8][nbrq]?$"},
        "comment": {"type": "string", "maxLength": 90},
    },
    "required": ["move", "comment"],
    "additionalProperties": False,
}

_REJECTED_REPLY_LIMIT = 300


def build_user_message(
    fen: str,
    history_san: str,
    white_last_uci: str,
    white_last_san: str,
    legal_moves: list[tuple[str, str]],
) -> str:
    legal_lines = "\n".join(f"- {uci} | {san}" for uci, san in legal_moves)
    return (
        f"FEN: {fen}\n"
        f"HISTORY_SAN: {history_san}\n"
        f"WHITE_LAST_MOVE: {white_last_uci} | {white_last_san}\n"
        f"LEGAL_MOVES:\n{legal_lines}\n"
        "\n"
        "Return the required JSON object."
    )


def build_corrective_message(original_user: str, raw_reply: str, reason: str) -> str:
    """One corrective request after a malformed or illegal reply: the
    rejected response, exactly why it failed, and the unchanged legal
    list via the original message."""
    rejected = raw_reply.strip()
    if len(rejected) > _REJECTED_REPLY_LIMIT:
        rejected = rejected[:_REJECTED_REPLY_LIMIT] + "..."
    return (
        f"Your previous reply was rejected: {reason}.\n"
        f"REJECTED_REPLY: {rejected}\n"
        "The board is unchanged. Choose exactly one move from LEGAL_MOVES.\n"
        "\n"
        f"{original_user}"
    )


def build_messages(system: str, user: str) -> list[dict]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
