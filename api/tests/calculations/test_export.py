import json

from euro_chess_studio.calculations.export import build_sft_rows, to_jsonl


def test_build_sft_rows_produces_prompt_completion_pairs():
    payloads = [
        {"fen": "startpos-fen", "legal_moves": ["e2e4", "d2d4"], "target_uci": "e2e4"},
    ]
    rows = build_sft_rows(payloads)
    assert len(rows) == 1
    assert "startpos-fen" in rows[0]["prompt"]
    assert "e2e4, d2d4" in rows[0]["prompt"]
    assert json.loads(rows[0]["completion"]) == {"move": "e2e4"}


def test_build_sft_rows_skips_malformed_payloads():
    payloads = [
        {"fen": "f", "legal_moves": ["e2e4"], "target_uci": "e2e4"},
        {"fen": "f", "legal_moves": "not-a-list", "target_uci": "e2e4"},
        {"legal_moves": ["e2e4"], "target_uci": "e2e4"},
        {"fen": "f", "legal_moves": ["e2e4"]},
    ]
    assert len(build_sft_rows(payloads)) == 1


def test_to_jsonl_one_object_per_line():
    rows = [{"a": 1}, {"b": 2}]
    text = to_jsonl(rows)
    lines = text.strip().split("\n")
    assert [json.loads(line) for line in lines] == rows
    assert text.endswith("\n")


def test_to_jsonl_empty_is_empty_string():
    assert to_jsonl([]) == ""
