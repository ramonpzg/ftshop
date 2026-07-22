"""Reply judgment: JSON object validation, scalar and list rejection,
deliberate code-fence tolerance, and legal-list membership."""

from chess_tui.calculations.replies import judge_move_reply

LEGAL = {"e7e5", "g8f6", "b8c6"}


def test_valid_reply():
    verdict = judge_move_reply('{"move": "e7e5", "comment": "Symmetry."}', LEGAL)
    assert verdict.status == "ok"
    assert verdict.move == "e7e5"
    assert verdict.comment == "Symmetry."


def test_code_fenced_reply_is_deliberately_tolerated():
    raw = '```json\n{"move": "g8f6", "comment": "Developing."}\n```'
    verdict = judge_move_reply(raw, LEGAL)
    assert verdict.status == "ok"
    assert verdict.move == "g8f6"


def test_uppercase_move_is_normalized():
    verdict = judge_move_reply('{"move": "E7E5", "comment": "Fine."}', LEGAL)
    assert verdict.status == "ok"
    assert verdict.move == "e7e5"


def test_multiline_comment_is_flattened():
    verdict = judge_move_reply('{"move": "e7e5", "comment": "One\\ntwo"}', LEGAL)
    assert verdict.comment == "One two"


def test_empty_reply_is_malformed():
    assert judge_move_reply("", LEGAL).status == "malformed_json"
    assert judge_move_reply("   ", LEGAL).status == "malformed_json"


def test_prose_is_malformed():
    verdict = judge_move_reply("I would play e5 here.", LEGAL)
    assert verdict.status == "malformed_json"


def test_scalar_json_is_rejected():
    assert judge_move_reply('"e7e5"', LEGAL).status == "malformed_json"


def test_list_json_is_rejected():
    assert judge_move_reply('["e7e5"]', LEGAL).status == "malformed_json"


def test_missing_move_is_wrong_shape():
    verdict = judge_move_reply('{"comment": "no move"}', LEGAL)
    assert verdict.status == "wrong_shape"
    assert "move" in verdict.reason


def test_non_string_move_is_wrong_shape():
    assert judge_move_reply('{"move": 5, "comment": "x"}', LEGAL).status == "wrong_shape"


def test_missing_comment_is_wrong_shape():
    verdict = judge_move_reply('{"move": "e7e5"}', LEGAL)
    assert verdict.status == "wrong_shape"
    assert "comment" in verdict.reason


def test_unlisted_move_is_illegal():
    verdict = judge_move_reply('{"move": "e2e4", "comment": "mine now"}', LEGAL)
    assert verdict.status == "illegal"
    assert verdict.move == "e2e4"
    assert "LEGAL_MOVES" in verdict.reason


def test_non_uci_move_is_illegal():
    verdict = judge_move_reply('{"move": "knight takes", "comment": "x"}', LEGAL)
    assert verdict.status == "illegal"


def test_extra_keys_are_tolerated_when_move_is_legal():
    raw = '{"move": "e7e5", "comment": "x", "why": "the schema forbids me"}'
    assert judge_move_reply(raw, LEGAL).status == "ok"
