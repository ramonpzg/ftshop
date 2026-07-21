"""Prompt and grammar construction from a real python-chess position.
The user message shape and the GBNF constraint are contracts the model
plays against; these tests pin them."""

import chess

from chess_tui.calculations.moves import legal_moves_uci_san, san_history_text
from chess_tui.calculations.prompt import (
    MOVE_PROMPT_VERSION,
    build_corrective_message,
    build_messages,
    build_move_grammar,
    build_user_message,
    system_prompt,
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
    assert lines[2] == "OPPONENT_LAST_MOVE: e2e4 | e4"
    assert lines[3] == "LEGAL_MOVES:"
    assert "- e7e5 | e5" in lines
    assert "- g8f6 | Nf6" in lines
    assert lines[-1] == "Return the required JSON object."
    assert sum(1 for line in lines if line.startswith("- ")) == len(legal)


def test_user_message_when_the_model_opens():
    legal = legal_moves_uci_san(chess.STARTING_FEN)
    message = build_user_message(chess.STARTING_FEN, "-", None, None, legal)
    assert "OPPONENT_LAST_MOVE: - (you move first)" in message
    assert "HISTORY_SAN: -" in message
    assert "- e2e4 | e4" in message


def test_system_prompt_is_color_parameterized():
    black = system_prompt("Black")
    white = system_prompt("White")
    assert "You are Black in a legal chess game" in black
    assert "You are White in a legal chess game" in white
    assert "legal White moves" in white
    assert "LEGAL_MOVES" in black
    assert '{"move":"<exact legal UCI>","comment":"<one short sentence>"}' in black


def test_grammar_enumerates_exactly_the_legal_moves():
    grammar = build_move_grammar(["e7e5", "g8f6"])
    assert 'move ::= "e7e5" | "g8f6"' in grammar
    assert grammar.startswith("root ::=")
    assert '"\\"move\\""' in grammar
    assert '"\\"comment\\""' in grammar
    assert "string ::=" in grammar


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
    messages = build_messages(system_prompt("Black"), "hello")
    assert [m["role"] for m in messages] == ["system", "user"]


def test_prompt_version_is_stamped():
    assert MOVE_PROMPT_VERSION == "tui-move-v3"
