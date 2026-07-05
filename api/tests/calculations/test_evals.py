from euro_chess_studio.calculations.evals import compute_legal_move_rate, compute_valid_json_rate


def test_legal_move_rate_is_none_with_no_moves():
    assert compute_legal_move_rate([]) is None


def test_legal_move_rate_all_legal():
    moves = [{"is_legal": 1}, {"is_legal": 1}]
    assert compute_legal_move_rate(moves) == 1.0


def test_legal_move_rate_mixed():
    moves = [{"is_legal": 1}, {"is_legal": 0}, {"is_legal": 1}, {"is_legal": 0}]
    assert compute_legal_move_rate(moves) == 0.5


def test_valid_json_rate_is_none_with_no_rows():
    assert compute_valid_json_rate([]) is None


def test_valid_json_rate_all_valid():
    rows = [{"payload_json": '{"a": 1}'}, {"payload_json": "[1, 2, 3]"}]
    assert compute_valid_json_rate(rows) == 1.0


def test_valid_json_rate_detects_invalid_payload():
    rows = [{"payload_json": '{"a": 1}'}, {"payload_json": "not json"}]
    assert compute_valid_json_rate(rows) == 0.5
