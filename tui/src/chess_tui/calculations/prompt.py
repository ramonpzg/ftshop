"""Prompt construction for the model turn. Pure, versioned, and the
only place the prompt text lives. Change the text only after a real
Gemma 4 test demonstrates why, and bump the version when you do.

Each model turn is a fresh, bounded request: the FEN plus compact
history carries the whole state, so no growing assistant conversation
is ever replayed."""

# v2 after a real Gemma 4 E2B Q4_0 test on llama.cpp 76f46ad showed
# the generic UCI pattern warping SAN-anchored intent ("e5") into
# pattern-valid junk ("e5b5"); constraining to the legal menu fixed
# it. v3 parameterizes the model's color (sides are now assigned at
# random) and ships the menu constraint as a raw GBNF grammar, which
# old llama.cpp server builds honor while response_format json_schema
# support varies. The application still validates membership.
MOVE_PROMPT_VERSION = "tui-move-v3"

_SYSTEM_PROMPT_TEMPLATE = """You are {color} in a legal chess game and a terse, dry chess coach.

The application is the only authority on the board and the rules. On every
turn it gives you the current FEN, the game history, your opponent's latest
move, and the complete set of legal {color} moves.

Choose exactly one move from LEGAL_MOVES. Copy its UCI value exactly. Never
invent a move, alter a move, claim that an unlisted move is legal, or return
more than one move.

Prefer, in order: checkmate; preventing forced loss; checks and forcing moves;
sound development and king safety; plans that can win while avoiding
unnecessary captures. Never avoid a necessary capture merely to satisfy the
last preference.

Write one short comment about the move or your opponent's preceding move. Be
dry, confident, and a little smug. Tie the comment to the actual position. Do
not use motivational filler, chess cliches, slurs, threats, identity-based
insults, or claims of engine certainty. Keep the comment under 90 characters.

Return one JSON object and nothing else:
{{"move":"<exact legal UCI>","comment":"<one short sentence>"}}

Do not use Markdown, code fences, analysis, reasoning, or additional keys."""

_REJECTED_REPLY_LIMIT = 300

# The comment string rule matches llama.cpp's own JSON grammar idiom:
# any printable character, standard escapes allowed. GBNF rules are
# one line each; the Python-side concatenation only serves the line
# length limit.
_GRAMMAR_TEMPLATE = (
    r'root ::= "{" ws "\"move\"" ws ":" ws "\"" move "\"" ws "," ws '
    r'"\"comment\"" ws ":" ws string ws "}"'
    "\n"
    "move ::= %MOVES%\n"
    r'string ::= "\"" ([^"\\\x7F\x00-\x1F] | "\\" (["\\/bfnrt] | "u" '
    r'[0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\""'
    "\n"
    r"ws ::= [ \t\n]*"
    "\n"
)


def system_prompt(model_color_name: str) -> str:
    """model_color_name is "White" or "Black"."""
    return _SYSTEM_PROMPT_TEMPLATE.format(color=model_color_name)


def build_move_grammar(legal_uci: list[str]) -> str:
    """GBNF for llama.cpp's raw `grammar` field: exactly move and
    comment, move constrained to the actual legal menu, not merely a
    UCI-shaped pattern (see MOVE_PROMPT_VERSION for the observed
    reason). Grammar output still does not replace chess validation;
    the application checks membership again on every reply."""
    alternation = " | ".join(f'"{uci}"' for uci in legal_uci)
    return _GRAMMAR_TEMPLATE.replace("%MOVES%", alternation)


def build_user_message(
    fen: str,
    history_san: str,
    opponent_last_uci: str | None,
    opponent_last_san: str | None,
    legal_moves: list[tuple[str, str]],
) -> str:
    legal_lines = "\n".join(f"- {uci} | {san}" for uci, san in legal_moves)
    if opponent_last_uci and opponent_last_san:
        last = f"{opponent_last_uci} | {opponent_last_san}"
    else:
        last = "- (you move first)"
    return (
        f"FEN: {fen}\n"
        f"HISTORY_SAN: {history_san}\n"
        f"OPPONENT_LAST_MOVE: {last}\n"
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
