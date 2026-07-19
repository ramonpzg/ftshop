"""Pure conversion from stored dataset rows to trainable SFT rows.

The exported format matches what the mini IDE and notebook snippets
consume: {"prompt": ..., "completion": ...} per line, prompt built with
the same template the prompt_template snippet teaches.
"""

import json

PROMPT_TEMPLATE = (
    "You are a chess engine assistant.\n\n"
    "Position (FEN): {fen}\n"
    "Legal moves (UCI): {legal_moves}\n\n"
    "Return exactly one move from the legal moves list, in UCI format.\n"
    'Respond with JSON: {{"move": "<uci>"}}'
)


def build_sft_rows(payloads: list[dict]) -> list[dict]:
    """fen_legal_moves_to_move payloads to prompt/completion rows.
    Payloads missing any needed field are skipped, not guessed at."""
    rows = []
    for payload in payloads:
        fen = payload.get("fen")
        legal_moves = payload.get("legal_moves")
        target = payload.get("target_uci")
        if not isinstance(fen, str) or not isinstance(legal_moves, list) or not target:
            continue
        rows.append(
            {
                "prompt": PROMPT_TEMPLATE.format(fen=fen, legal_moves=", ".join(legal_moves)),
                "completion": json.dumps({"move": target}),
            }
        )
    return rows


def to_jsonl(rows: list[dict]) -> str:
    return "\n".join(json.dumps(row) for row in rows) + ("\n" if rows else "")


def build_scenario_export_rows(scenarios: list[dict]) -> list[dict]:
    """Stored scenario rows to export rows. The raw suggestion and the
    participant-approved text stay separate: `approved` is null until a
    participant accepted or edited, so a presenter reading the export
    can tell model output from vetted examples. Failed rows are skipped;
    they carry no scenario to train on."""
    rows = []
    for scenario in scenarios:
        if scenario["status"] == "failed":
            continue
        approved = None
        if scenario["status"] in ("accepted", "edited"):
            approved = {
                "assessment": scenario["final_assessment"],
                "real_world": scenario["final_real_world"],
                "video_prompt": scenario["final_video_prompt"],
            }
        rows.append(
            {
                "workspace_id": scenario["workspace_id"],
                "game_id": scenario["game_id"],
                "ply": scenario["ply"],
                "fen": scenario["fen"],
                "status": scenario["status"],
                "suggested": {
                    "assessment": scenario["suggested_assessment"],
                    "real_world": scenario["suggested_real_world"],
                    "video_prompt": scenario["suggested_video_prompt"],
                },
                "approved": approved,
                "model": scenario["model"],
                "provider_alias": scenario["provider_alias"],
                "prompt_version": scenario["prompt_version"],
                "created_at": scenario["created_at"],
                "updated_at": scenario["updated_at"],
            }
        )
    return rows
