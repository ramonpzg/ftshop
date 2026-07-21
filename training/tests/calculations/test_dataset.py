import json

from chess_adapt.calculations.dataset import (
    ENRICHMENT_SCHEMA,
    SelectionConfig,
    build_enrichment_messages,
    build_sft_rows,
    content_hash,
    domain_for_game,
    select_game,
    split_for_game,
)


def source_row(movetext: str = "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0") -> dict:
    return {
        "Event": "Rated Blitz game",
        "Site": "https://lichess.org/testgame",
        "Result": "1-0",
        "White": "not-copied",
        "Black": "not-copied-either",
        "WhiteElo": 1500,
        "BlackElo": 1510,
        "UTCDate": None,
        "UTCTime": None,
        "ECO": "C20",
        "Opening": "King's Pawn Game",
        "Termination": "Normal",
        "TimeControl": "180+0",
        "movetext": movetext,
    }


def selected_game() -> dict:
    game = select_game(source_row(), SelectionConfig(limit=1, scan_limit=1))
    assert game is not None
    return game


def test_select_game_accepts_real_checkmate_and_drops_usernames():
    game = selected_game()
    assert game["ply_count"] == 7
    assert game["winner_capture_count"] == 1
    assert game["winner_captured_pieces"] == ["pawn"]
    assert game["winner"] == "white"
    assert "White" not in game
    assert "Black" not in game


def test_select_game_enforces_capture_and_checkmate_filters():
    assert (
        select_game(
            source_row(),
            SelectionConfig(limit=1, scan_limit=1, max_winner_captures=0),
        )
        is None
    )
    assert select_game(source_row("1. e4 e5 2. Nf3 Nc6 1/2-1/2"), SelectionConfig()) is None


def test_enrichment_prompt_describes_game_and_bans_literal_chess_video():
    messages = build_enrichment_messages(selected_game())
    assert "checkmate in 4 moves" in messages[1]["content"]
    assert "winner captured 1 pieces" in messages[1]["content"]
    assert "never a chessboard" in messages[0]["content"]
    assert (
        f"Assigned setting: {domain_for_game(selected_game()['game_id'])}" in messages[1]["content"]
    )
    assert "rather than a generic security" in messages[1]["content"]


def test_sft_rows_keep_move_and_scenario_in_one_game_split():
    game = selected_game()
    enrichment = {
        game["game_id"]: {
            "schema_version": ENRICHMENT_SCHEMA,
            "status": "succeeded",
            "assessment": "A direct attack wins before material matters.",
            "real_world": "A small team removes one blocker and reaches the decision maker.",
            "video_prompt": "A small rescue team crosses a quiet loading bay.",
        }
    }
    rows = build_sft_rows([game], enrichment, split_seed=7)
    assert {row["task"] for row in rows} == {"move", "scenario"}
    assert {row["split"] for row in rows} == {split_for_game(game["game_id"], 7)}
    move_rows = [row for row in rows if row["task"] == "move"]
    assert len(move_rows) == 4
    for row in move_rows:
        completion = json.loads(row["messages"][-1]["content"])
        assert completion["move"] in row["legal_moves"]


def test_content_hash_is_order_independent_and_duplicate_sensitive():
    first = {"a": 1}
    second = {"b": 2}
    assert content_hash([first, second]) == content_hash([second, first])
    assert content_hash([first, second]) != content_hash([first, second, second])
