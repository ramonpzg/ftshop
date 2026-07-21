"""Orchestration for selection, enrichment, and saved SFT splits."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from euro_chess_studio.calculations.llm_prompts import parse_assess_reply

from chess_adapt.calculations.dataset import (
    ENRICHMENT_SCHEMA,
    SelectionConfig,
    build_enrichment_messages,
    build_sft_rows,
    content_hash,
    select_game,
)
from chess_adapt.data.lichess import open_source
from chess_adapt.data.store import PipelinePaths, read_json, read_jsonl, write_json, write_jsonl

EnrichOne = Callable[[list[dict[str, str]]], dict[str, Any]]
EnrichmentProgress = Callable[[int, int, str], None]


@dataclass(frozen=True)
class PreparationSummary:
    scanned: int
    selected: int
    games_path: str


@dataclass(frozen=True)
class EnrichmentSummary:
    attempted: int
    succeeded: int
    failed: int
    already_succeeded: int
    stopped_after_failures: bool


def prepare_sample(
    paths: PipelinePaths,
    config: SelectionConfig,
    *,
    offline: bool = False,
) -> PreparationSummary:
    config.validate()
    source, rows = open_source(offline=offline)
    selected: list[dict[str, Any]] = []
    scanned = 0
    for row in rows:
        if scanned >= config.scan_limit or len(selected) >= config.limit:
            break
        scanned += 1
        game = select_game(row, config)
        if game is not None:
            selected.append(game)

    if len(selected) < config.limit:
        raise RuntimeError(
            f"selected {len(selected)} games after scanning {scanned}; "
            f"requested {config.limit}. Raise --scan-limit or relax the filters."
        )

    write_jsonl(paths.games, selected)
    manifest = {
        "schema_version": "chess-adapt-manifest-v1",
        "created_at": _now(),
        "source": {
            "dataset_id": source.dataset_id,
            "revision": source.revision,
            "filename": source.filename,
            "license": source.license,
            "source_rows": source.row_count,
        },
        "selection": asdict(config),
        "scanned_count": scanned,
        "selected_game_count": len(selected),
        "selected_games_hash": content_hash(selected),
        "privacy": "Source usernames are not copied into the processed sample.",
    }
    write_json(paths.manifest, manifest)
    rebuild_sft(paths, config.split_seed)
    return PreparationSummary(scanned=scanned, selected=len(selected), games_path=str(paths.games))


def enrich_sample(
    paths: PipelinePaths,
    enrich_one: EnrichOne,
    *,
    split_seed: int,
    limit: int | None = None,
    max_consecutive_failures: int = 3,
    progress: EnrichmentProgress | None = None,
) -> EnrichmentSummary:
    games = read_jsonl(paths.games)
    if not games:
        raise RuntimeError(f"no prepared games at {paths.games}; run --prepare first")
    existing = {row["game_id"]: row for row in read_jsonl(paths.enrichments)}
    already_succeeded = sum(_is_current_success(row) for row in existing.values())
    attempted = succeeded = failed = consecutive_failures = 0
    stopped = False

    for game in games:
        if _is_current_success(existing.get(game["game_id"], {})):
            continue
        if limit is not None and attempted >= limit:
            break
        attempted += 1
        outcome: dict[str, Any] | None = None
        try:
            outcome = enrich_one(build_enrichment_messages(game))
            raw_reply = outcome["raw_reply"]
            parsed = parse_assess_reply(raw_reply)
            if parsed is None:
                raise ValueError("reply did not contain the three required JSON strings")
            record = {
                "schema_version": ENRICHMENT_SCHEMA,
                "game_id": game["game_id"],
                "status": "succeeded",
                **parsed,
                **{key: value for key, value in outcome.items() if key != "raw_reply"},
                "raw_reply": raw_reply,
                "updated_at": _now(),
            }
            existing[game["game_id"]] = record
            succeeded += 1
            consecutive_failures = 0
        except Exception as exc:
            failed += 1
            consecutive_failures += 1
            existing[game["game_id"]] = {
                "schema_version": ENRICHMENT_SCHEMA,
                "game_id": game["game_id"],
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
                **_failure_provenance(exc, outcome),
                "updated_at": _now(),
            }
        finally:
            # One atomic checkpoint per provider call. A dropped connection
            # or interrupted terminal loses at most the in-flight request.
            ordered = [existing[game["game_id"]] for game in games if game["game_id"] in existing]
            write_jsonl(paths.enrichments, ordered)
            if progress is not None:
                progress(
                    already_succeeded + attempted,
                    len(games),
                    existing[game["game_id"]]["status"],
                )

        if consecutive_failures >= max_consecutive_failures:
            stopped = True
            break

    rebuild_sft(paths, split_seed)
    return EnrichmentSummary(
        attempted=attempted,
        succeeded=succeeded,
        failed=failed,
        already_succeeded=already_succeeded,
        stopped_after_failures=stopped,
    )


def rebuild_sft(paths: PipelinePaths, split_seed: int) -> dict[str, int]:
    games = read_jsonl(paths.games)
    enrichments = {row["game_id"]: row for row in read_jsonl(paths.enrichments)}
    rows = build_sft_rows(games, enrichments, split_seed=split_seed)
    counts: dict[str, int] = {}
    for split in ("train", "validation", "test"):
        split_rows = [row for row in rows if row["split"] == split]
        write_jsonl(paths.split(split), split_rows)
        counts[split] = len(split_rows)

    manifest = read_json(paths.manifest)
    manifest["updated_at"] = _now()
    manifest["enriched_game_count"] = sum(_is_current_success(row) for row in enrichments.values())
    manifest["sft"] = {
        "schema_version": "gemma-chat-sft-v1",
        "content_hash": content_hash(rows),
        "row_count": len(rows),
        "split_counts": counts,
        "tasks": {task: sum(row["task"] == task for row in rows) for task in ("move", "scenario")},
        "split_unit": "game",
    }
    write_json(paths.manifest, manifest)
    return counts


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _is_current_success(row: dict[str, Any]) -> bool:
    return row.get("status") == "succeeded" and row.get("schema_version") == ENRICHMENT_SCHEMA


def _failure_provenance(exc: Exception, outcome: dict[str, Any] | None) -> dict[str, Any]:
    if outcome is not None:
        return dict(outcome)
    fields = {}
    for name in (
        "status_code",
        "request_ids",
        "transport_attempts",
        "json_mode_dropped",
        "reasoning_effort_dropped",
    ):
        value = getattr(exc, name, None)
        if value is not None:
            fields[name] = list(value) if isinstance(value, tuple) else value
    return fields
