"""Actions for the real-world scenario mapping.

Every suggestion call is persisted: the raw model reply lands in
model_attempts whether or not it parses, and the scenario row keeps the
suggested text immutable while participant review writes the final_*
columns. A failed call inserts a 'failed' scenario row with its reason;
prior records are never erased, so the state is recoverable by simply
asking again.
"""

import sqlite3

from euro_chess_studio.actions.errors import (
    ModelReplyError,
    ScenarioNotFoundError,
    ScenarioReviewError,
    WorkspaceNotFoundError,
)
from euro_chess_studio.calculations.llm_prompts import (
    ASSESS_PROMPT_VERSION,
    build_assess_messages,
    parse_assess_reply,
)
from euro_chess_studio.data import llm_client
from euro_chess_studio.data.games_repo import get_active_game
from euro_chess_studio.data.model_attempts_repo import insert_attempt
from euro_chess_studio.data.moves_repo import list_legal_sans
from euro_chess_studio.data.scenario_repo import (
    get_scenario,
    insert_scenario,
    latest_scenario,
    set_review,
)
from euro_chess_studio.data.workspaces_repo import get_workspace


def suggest_scenario(conn: sqlite3.Connection, workspace_id: str) -> sqlite3.Row:
    """Asks the scene-writing model for the three-field mapping and
    persists the whole exchange against the game and ply."""
    workspace = get_workspace(conn, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError(f"unknown workspace id: {workspace_id}")

    active = get_active_game(conn, workspace_id)
    game_id = active["id"] if active is not None else None
    sans = list_legal_sans(conn, workspace_id, game_id)
    ply = len(sans)
    fen = workspace["board_fen"]
    requested_model = llm_client.get_video_prompt_model()

    def record_attempt(**fields) -> sqlite3.Row:
        return insert_attempt(
            conn,
            workspace_id=workspace_id,
            game_id=game_id,
            task="scenario",
            actor="model",
            model=fields.pop("model", requested_model),
            provider_alias=fields.pop("provider_alias", "video_prompt"),
            prompt_version=ASSESS_PROMPT_VERSION,
            ply=ply,
            fen=fen,
            attempt_number=1,
            json_requested=True,
            **fields,
        )

    def record_failure(attempt: sqlite3.Row, error_detail: str) -> None:
        insert_scenario(
            conn,
            workspace_id=workspace_id,
            game_id=game_id,
            attempt_id=attempt["id"],
            ply=ply,
            fen=fen,
            status="failed",
            model=attempt["model"],
            provider_alias=attempt["provider_alias"],
            prompt_version=ASSESS_PROMPT_VERSION,
            error_detail=error_detail,
        )
        conn.commit()

    try:
        reply = llm_client.video_prompt_chat(build_assess_messages(sans, fen))
    except llm_client.LlmRequestError as exc:
        attempt = record_attempt(
            status="transport_failed",
            error_detail=str(exc)[:400],
            request_ids=exc.request_ids,
        )
        record_failure(attempt, str(exc)[:400])
        raise

    # The raw reply is stored in the same transaction whether or not it
    # parses; a garbage reply is still evidence.
    parsed = parse_assess_reply(reply.content)
    if parsed is None:
        attempt = record_attempt(
            status="parse_failed",
            raw_response=reply.content,
            model=reply.model,
            provider_alias=reply.provider_alias,
            request_ids=reply.request_ids,
        )
        record_failure(attempt, "reply had no usable assessment")
        raise ModelReplyError(f"model reply had no usable assessment: {reply.content[:200]}")

    attempt = record_attempt(
        status="ok",
        raw_response=reply.content,
        parse_ok=True,
        model=reply.model,
        provider_alias=reply.provider_alias,
        request_ids=reply.request_ids,
    )
    scenario = insert_scenario(
        conn,
        workspace_id=workspace_id,
        game_id=game_id,
        attempt_id=attempt["id"],
        ply=ply,
        fen=fen,
        status="suggested",
        suggested_assessment=parsed["assessment"],
        suggested_real_world=parsed["real_world"],
        suggested_video_prompt=parsed["video_prompt"],
        model=reply.model,
        provider_alias=reply.provider_alias,
        prompt_version=ASSESS_PROMPT_VERSION,
    )
    conn.commit()
    return scenario


def review_scenario(
    conn: sqlite3.Connection,
    scenario_id: str,
    *,
    accept: bool,
    assessment: str | None = None,
    real_world: str | None = None,
    video_prompt: str | None = None,
) -> sqlite3.Row:
    """Records the participant's accept (final = suggested) or edit
    (final = provided text). The raw suggestion stays untouched."""
    scenario = get_scenario(conn, scenario_id)
    if scenario is None:
        raise ScenarioNotFoundError(f"unknown scenario id: {scenario_id}")
    if scenario["status"] == "failed":
        raise ScenarioReviewError("a failed suggestion cannot be reviewed; ask again instead")

    if accept:
        status = "accepted"
        final_assessment = str(scenario["suggested_assessment"])
        final_real_world = str(scenario["suggested_real_world"])
        final_video_prompt = str(scenario["suggested_video_prompt"])
    else:
        if not assessment or not assessment.strip():
            raise ScenarioReviewError("an edit needs all three fields, none of them empty")
        if not real_world or not real_world.strip():
            raise ScenarioReviewError("an edit needs all three fields, none of them empty")
        if not video_prompt or not video_prompt.strip():
            raise ScenarioReviewError("an edit needs all three fields, none of them empty")
        status = "edited"
        final_assessment = assessment
        final_real_world = real_world
        final_video_prompt = video_prompt

    row = set_review(
        conn,
        scenario_id,
        status=status,
        final_assessment=final_assessment,
        final_real_world=final_real_world,
        final_video_prompt=final_video_prompt,
    )
    conn.commit()
    return row


def latest_scenario_for_workspace(
    conn: sqlite3.Connection, workspace_id: str
) -> sqlite3.Row | None:
    if get_workspace(conn, workspace_id) is None:
        raise WorkspaceNotFoundError(f"unknown workspace id: {workspace_id}")
    return latest_scenario(conn, workspace_id)
