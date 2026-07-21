"""Prompt construction from a real python-chess position. The user
message shape is a contract the model was prompted against; these
tests pin it."""

import chess

from chess_tui.calculations.moves import legal_moves_uci_san, san_history_text
from chess_tui.calculations.prompt import (
    MOVE_PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_corrective_message,
    build_messages,
    build_user_message,
    move_json_schema,
)


def _position_after_e4() -> chess.Board:
    board = chess.Board()
    board.push_uci("e2e4")
    return board


def test_user_message_shape():
    board = _position_after_e4()
    legal = legal_moves_uci_san(board.fen())
    message = build_user_message(board.fen(), san_history_text(["e4"]), "e2e4", "e4", legal)
    lines = message.splitlines()
    assert lines[0] == f"FEN: {board.fen()}"
    assert lines[1] == "HISTORY_SAN: 1. e4"
    assert lines[2] == "WHITE_LAST_MOVE: e2e4 | e4"
    assert lines[3] == "LEGAL_MOVES:"
    assert "- e7e5 | e5" in lines
    assert "- g8f6 | Nf6" in lines
    assert lines[-1] == "Return the required JSON object."
    # every legal black reply is listed exactly once
    assert sum(1 for line in lines if line.startswith("- ")) == len(legal)


def test_corrective_message_names_rejection_and_repeats_the_list():
    original = "FEN: x\nLEGAL_MOVES:\n- e7e5 | e5\n\nReturn the required JSON object."
    corrective = build_corrective_message(original, '{"move":"e2e4"}', "not in LEGAL_MOVES")
    assert "rejected: not in LEGAL_MOVES" in corrective
    assert 'REJECTED_REPLY: {"move":"e2e4"}' in corrective
    assert corrective.endswith(original)


def test_corrective_message_bounds_giant_replies():
    corrective = build_corrective_message("original", "x" * 1000, "reason")
    assert "x" * 301 not in corrective
    assert "..." in corrective


def test_messages_are_system_then_user():
    messages = build_messages(SYSTEM_PROMPT, "hello")
    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[0]["content"] is SYSTEM_PROMPT


def test_schema_constrains_move_to_the_legal_menu():
    schema = move_json_schema(["e7e5", "g8f6"])
    assert schema["required"] == ["move", "comment"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["comment"]["maxLength"] == 90
    assert schema["properties"]["move"]["enum"] == ["e7e5", "g8f6"]


def test_prompt_version_is_stamped():
    assert MOVE_PROMPT_VERSION == "tui-move-v2"
    assert "LEGAL_MOVES" in SYSTEM_PROMPT
