import json

from euro_chess_studio.calculations.export import build_sft_rows, is_training_eligible, to_jsonl


def test_build_sft_rows_produces_prompt_completion_pairs():
    payloads = [
        {
            "fen": "startpos-fen",
            "legal_moves": ["e2e4", "d2d4"],
            "target_uci": "e2e4",
            "actor": "participant",
        },
    ]
    rows = build_sft_rows(payloads)
    assert len(rows) == 1
    assert "startpos-fen" in rows[0]["prompt"]
    assert "e2e4, d2d4" in rows[0]["prompt"]
    assert json.loads(rows[0]["completion"]) == {"move": "e2e4"}


def test_build_sft_rows_skips_malformed_payloads():
    payloads = [
        {"fen": "f", "legal_moves": ["e2e4"], "target_uci": "e2e4", "actor": "participant"},
        {
            "fen": "f",
            "legal_moves": "not-a-list",
            "target_uci": "e2e4",
            "actor": "participant",
        },
        {"legal_moves": ["e2e4"], "target_uci": "e2e4", "actor": "participant"},
        {"fen": "f", "legal_moves": ["e2e4"], "actor": "participant"},
    ]
    assert len(build_sft_rows(payloads)) == 1


def test_build_sft_rows_excludes_fallback_moves():
    """A fallback move is a deterministic placeholder, not a real answer;
    training on it would teach an arbitrary lexicographic choice as if
    it were skill."""
    payloads = [
        {"fen": "f", "legal_moves": ["e2e4"], "target_uci": "e2e4", "actor": "participant"},
        {"fen": "f", "legal_moves": ["a2a3"], "target_uci": "a2a3", "actor": "fallback"},
        {"fen": "f", "legal_moves": ["e7e5"], "target_uci": "e7e5", "actor": "model"},
        {"fen": "f", "legal_moves": ["d2d4"], "target_uci": "d2d4", "actor": "unknown"},
        {"fen": "f", "legal_moves": ["d2d4"], "target_uci": "d2d4"},  # no actor at all
    ]
    rows = build_sft_rows(payloads)
    assert len(rows) == 2
    completions = {json.loads(row["completion"])["move"] for row in rows}
    assert completions == {"e2e4", "e7e5"}


def test_is_training_eligible():
    assert is_training_eligible("participant") is True
    assert is_training_eligible("model") is True
    assert is_training_eligible("fallback") is False
    assert is_training_eligible("unknown") is False
    assert is_training_eligible(None) is False


def test_to_jsonl_one_object_per_line():
    rows = [{"a": 1}, {"b": 2}]
    text = to_jsonl(rows)
    lines = text.strip().split("\n")
    assert [json.loads(line) for line in lines] == rows
    assert text.endswith("\n")


def test_to_jsonl_empty_is_empty_string():
    assert to_jsonl([]) == ""
