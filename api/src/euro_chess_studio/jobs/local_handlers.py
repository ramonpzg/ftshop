"""Local job handlers: tiny real calculations over the app's own data.
Each handler may also persist eval_results, since running the job is what
makes those numbers real rather than fabricated.
"""

import sqlite3
from collections.abc import Callable

from euro_chess_studio.calculations.audio import synthesize_spectrogram
from euro_chess_studio.calculations.evals import compute_legal_move_rate, compute_valid_json_rate
from euro_chess_studio.calculations.video import uniform_frame_indices
from euro_chess_studio.data.dataset_rows_repo import list_dataset_rows
from euro_chess_studio.data.eval_results_repo import replace_eval_result
from euro_chess_studio.data.moves_repo import list_moves
from euro_chess_studio.jobs.base import JobConfig, JobOutput


def text_prompt_eval(conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
    moves = list_moves(conn, job.workspace_id) if job.workspace_id else []
    dataset_rows = list_dataset_rows(conn, job.workspace_id) if job.workspace_id else []

    legal_move_rate = compute_legal_move_rate(moves)
    valid_json_rate = compute_valid_json_rate(dataset_rows)

    if legal_move_rate is not None:
        replace_eval_result(
            conn,
            modality="text",
            metric="legal_move_rate",
            value=legal_move_rate,
            workspace_id=job.workspace_id,
            source="computed",
        )
    if valid_json_rate is not None:
        replace_eval_result(
            conn,
            modality="text",
            metric="valid_json_rate",
            value=valid_json_rate,
            workspace_id=job.workspace_id,
            source="computed",
        )

    return JobOutput(
        modality="text",
        kind="prompt_eval",
        payload={
            "move_count": len(moves),
            "legal_move_rate": legal_move_rate,
            "valid_json_rate": valid_json_rate,
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
