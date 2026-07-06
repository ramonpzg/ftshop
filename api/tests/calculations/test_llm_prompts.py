from euro_chess_studio.calculations.llm_prompts import (
    build_assess_messages,
    build_move_messages,
    parse_assess_reply,
    parse_move_reply,
)


def test_move_messages_carry_fen_and_legal_moves():
    messages = build_move_messages("some-fen", ["e2e4", "d2d4"])
    assert messages[0]["role"] == "system"
    assert "some-fen" in messages[1]["content"]
    assert "e2e4, d2d4" in messages[1]["content"]


def test_assess_messages_carry_history_and_fen():
    messages = build_assess_messages(["e4", "e5"], "some-fen")
    assert "e4 e5" in messages[1]["content"]
    assert "some-fen" in messages[1]["content"]


def test_assess_messages_handle_empty_history():
    messages = build_assess_messages([], "some-fen")
    assert "(no moves yet)" in messages[1]["content"]


def test_parse_move_reply_plain_json():
    assert parse_move_reply('{"move": "e2e4"}') == "e2e4"


def test_parse_move_reply_fenced_json():
    assert parse_move_reply('Sure!\n```json\n{"move": "G1F3"}\n```') == "g1f3"


def test_parse_move_reply_with_promotion():
    assert parse_move_reply('{"move": "a7a8q"}') == "a7a8q"


def test_parse_move_reply_rejects_garbage():
    assert parse_move_reply("I'd play e4 here.") is None
    assert parse_move_reply('{"move": "castle kingside"}') is None
    assert parse_move_reply('{"best": "e2e4"}') is None


def test_parse_assess_reply_happy_path():
    reply = '{"assessment": "White is better.", "real_world": "Like a tidy inbox."}'
    assert parse_assess_reply(reply) == {
        "assessment": "White is better.",
        "real_world": "Like a tidy inbox.",
    }


def test_parse_assess_reply_tolerates_missing_real_world():
    assert parse_assess_reply('{"assessment": "Equal."}') == {
        "assessment": "Equal.",
        "real_world": "",
    }


def test_parse_assess_reply_rejects_garbage():
    assert parse_assess_reply("The position is fine.") is None
    assert parse_assess_reply('{"real_world": "no assessment here"}') is None
