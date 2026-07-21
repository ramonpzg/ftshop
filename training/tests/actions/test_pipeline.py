from chess_adapt.actions.pipeline import enrich_sample, rebuild_sft
from chess_adapt.calculations.dataset import SelectionConfig, select_game
from chess_adapt.data.store import PipelinePaths, read_jsonl, write_json, write_jsonl


def game(site: str) -> dict:
    row = {
        "Event": "Rated Blitz game",
        "Site": site,
        "Result": "1-0",
        "WhiteElo": 1500,
        "BlackElo": 1510,
        "UTCDate": None,
        "UTCTime": None,
        "ECO": "C20",
        "Opening": "King's Pawn Game",
        "Termination": "Normal",
        "TimeControl": "180+0",
        "movetext": "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0",
    }
    selected = select_game(row, SelectionConfig(limit=1, scan_limit=1))
    assert selected is not None
    return selected


def paths(tmp_path) -> PipelinePaths:
    result = PipelinePaths(tmp_path / "data", tmp_path / "output")
    games = [game("https://lichess.org/one"), game("https://lichess.org/two")]
    write_jsonl(result.games, games)
    write_json(
        result.manifest,
        {
            "schema_version": "chess-adapt-manifest-v1",
            "selection": {"split_seed": 7},
        },
    )
    rebuild_sft(result, 7)
    return result


def successful_reply(messages):
    assert messages[-1]["role"] == "user"
    return {
        "raw_reply": (
            '{"assessment":"Direct pressure",'
            '"real_world":"A small team clears one blocker and reaches the decision maker.",'
            '"video_prompt":"A small team walks through a loading bay toward one closed door."}'
        ),
        "model": "gpt-5.6-luna",
        "request_ids": ["req-test"],
    }


def test_enrichment_checkpoints_and_skips_successes_on_resume(tmp_path):
    pipeline_paths = paths(tmp_path)
    first = enrich_sample(pipeline_paths, successful_reply, split_seed=7, limit=1)
    assert first.succeeded == 1

    calls = 0

    def count_reply(messages):
        nonlocal calls
        calls += 1
        return successful_reply(messages)

    second = enrich_sample(pipeline_paths, count_reply, split_seed=7)
    assert second.already_succeeded == 1
    assert second.succeeded == 1
    assert calls == 1


def test_enrichment_stops_after_three_consecutive_failures(tmp_path):
    pipeline_paths = paths(tmp_path)

    def fail(_messages):
        raise RuntimeError("provider down")

    summary = enrich_sample(
        pipeline_paths,
        fail,
        split_seed=7,
        max_consecutive_failures=1,
    )
    assert summary.failed == 1
    assert summary.stopped_after_failures is True


def test_invalid_reply_is_saved_raw_for_review(tmp_path):
    pipeline_paths = paths(tmp_path)

    def invalid(_messages):
        return {
            "raw_reply": "not JSON",
            "model": "gpt-5.6-luna",
            "request_ids": ["req-invalid"],
        }

    summary = enrich_sample(pipeline_paths, invalid, split_seed=7, limit=1)
    assert summary.failed == 1
    failed = read_jsonl(pipeline_paths.enrichments)[0]
    assert failed["raw_reply"] == "not JSON"
    assert failed["request_ids"] == ["req-invalid"]
