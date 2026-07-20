"""Local job handlers: tiny real calculations over the app's own data.
Each handler may also persist eval_results, since running the job is what
makes those numbers real rather than fabricated.
"""

import json
import sqlite3
from collections.abc import Callable
from dataclasses import asdict

from euro_chess_studio.calculations.audio import synthesize_spectrogram
from euro_chess_studio.calculations.evals import (
    MetricResult,
    compute_legal_move_rate,
    compute_model_legal_move_rate,
    compute_position_set_id,
    compute_valid_json_rate,
)
from euro_chess_studio.calculations.ids import generate_id
from euro_chess_studio.calculations.video import uniform_frame_indices
from euro_chess_studio.data.eval_results_repo import delete_eval_result, replace_eval_result
from euro_chess_studio.data.model_attempts_repo import list_attempts
from euro_chess_studio.data.moves_repo import list_moves
from euro_chess_studio.jobs.base import JobConfig, JobOutput


def _persist_metric(
    conn: sqlite3.Connection, workspace_id: str | None, result: MetricResult, run_id: str
) -> None:
    """An available metric replaces any prior result for its exact scope
    and position set (model, checkpoint, which positions it covered, and
    the rest of the identity together): the same window re-run updates
    in place, a genuinely different window (a different position set)
    coexists instead of overwriting. An unavailable metric removes every
    window's prior result for the scope instead of leaving one on
    display: an empty sample must not keep showing a stale number from
    before the data disappeared (a page reset, for instance), and has no
    position set to target a single window's row with anyway."""
    model = result.scope.get("model")
    checkpoint = result.scope.get("checkpoint")
    if not result.available or result.value is None:
        delete_eval_result(
            conn,
            modality="text",
            metric=result.metric,
            workspace_id=workspace_id,
            source="computed",
            model=model,
            checkpoint=checkpoint,
        )
        return
    position_set_id = compute_position_set_id(result.positions)
    replace_eval_result(
        conn,
        modality="text",
        metric=result.metric,
        value=result.value,
        workspace_id=workspace_id,
        source="computed",
        numerator=result.numerator,
        denominator=result.denominator,
        unit=result.unit,
        direction=result.direction,
        definition=result.definition,
        version=result.version,
        scope_json=json.dumps(result.scope),
        model=model,
        checkpoint=checkpoint,
        run_id=run_id,
        sample_ids_json=json.dumps(list(result.sample_ids)),
        position_set_id=position_set_id,
        position_set_json=json.dumps(list(result.positions)),
    )


def text_prompt_eval(conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
    """Optional job.params "model" and "checkpoint" scope the model-facing
    metrics to one version, so a base and an adapted model's results can
    be run and stored side by side instead of one overwriting the
    other. Unscoped (the default) mixes every model/checkpoint for the
    workspace, matching prior behavior."""
    model = job.params.get("model")
    checkpoint = job.params.get("checkpoint")
    moves = list_moves(conn, job.workspace_id) if job.workspace_id else []
    attempts = (
        list_attempts(conn, workspace_id=job.workspace_id, task="move") if job.workspace_id else []
    )

    run_id = generate_id("evalrun")
    results = [
        compute_legal_move_rate(moves, actor="participant"),
        compute_model_legal_move_rate(attempts, model=model, checkpoint=checkpoint),
        compute_valid_json_rate(attempts, task="move", model=model, checkpoint=checkpoint),
    ]
    for result in results:
        _persist_metric(conn, job.workspace_id, result, run_id)

    return JobOutput(
        modality="text",
        kind="prompt_eval",
        payload={
            "move_count": len(moves),
            "model_attempt_count": len(attempts),
            "run_id": run_id,
            "metrics": [asdict(result) for result in results],
        },
    )


def text_reward_eval(conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
    moves = list_moves(conn, job.workspace_id) if job.workspace_id else []
    rewards = [{"ply": move["ply"], "uci": move["uci"], "reward": move["reward"]} for move in moves]
    total_reward = sum(move["reward"] for move in moves)
    return JobOutput(
        modality="text",
        kind="reward_eval",
        payload={"total_reward": total_reward, "rewards": rewards},
    )


def audio_make_spectrogram(conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
    duration_seconds = job.params.get("duration_seconds", 0.4)
    tags = job.params.get("tags", ["capture", "wood", "impact"])
    spectrogram = synthesize_spectrogram(duration_seconds, tags)
    return JobOutput(
        modality="audio",
        kind="spectrogram",
        payload={"duration_seconds": duration_seconds, "tags": tags, "spectrogram": spectrogram},
    )


def video_sample_frames(conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
    total_frames = job.params.get("total_frames", 120)
    fps = job.params.get("fps", 24)
    num_samples = job.params.get("num_samples", 8)
    indices = uniform_frame_indices(total_frames, num_samples)
    return JobOutput(
        modality="video",
        kind="frame_sample",
        payload={
            "total_frames": total_frames,
            "fps": fps,
            "sampled_indices": indices,
            "sampled_seconds": [round(i / fps, 2) for i in indices],
        },
    )


LOCAL_HANDLERS: dict[str, Callable[[sqlite3.Connection, JobConfig], JobOutput]] = {
    "text.prompt_eval": text_prompt_eval,
    "text.reward_eval": text_reward_eval,
    "audio.make_spectrogram": audio_make_spectrogram,
    "video.sample_frames": video_sample_frames,
}
