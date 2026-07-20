"""Pure conversion from stored dataset rows to trainable SFT rows.

The exported format matches what the mini IDE and notebook snippets
consume: {"prompt": ..., "completion": ...} per line, prompt built with
the same template the prompt_template snippet teaches.
"""

import json

# The "why" field is explicitly optional: including it is invited, not
# required, so a bare {"move": ...} reply still satisfies the contract.
# That is what lets explanation_rate measure a real trade-off instead
# of rewarding contract violations -- a model that explains inside the
# JSON is doing something the prompt asked for, and a model that stopped
# explaining after bare-completion training regressed on an invited
# behavior, not on politeness.
PROMPT_TEMPLATE = (
    "You are a chess engine assistant.\n\n"
    "Position (FEN): {fen}\n"
    "Legal moves (UCI): {legal_moves}\n\n"
    "Return exactly one move from the legal moves list, in UCI format.\n"
    "You may add a one-sentence reason in the optional why field.\n"
    'Respond with JSON: {{"move": "<uci>", "why": "<optional short reason>"}}'
)

# Versions the prompt contract above. Training snapshots and evaluation
# suites both record it; a benchmark comparison refuses to produce a
# delta across two different contracts. Bump when PROMPT_TEMPLATE
# changes meaningfully. v2 added the optional why field.
SFT_PROMPT_VERSION = "sft-v2"

# Fallback moves are a deterministic placeholder played specifically
# because the model produced no usable reply (see actions/model_turn.py);
# they are not a legitimate SFT target, and training on them would teach
# "always play the alphabetically first legal move" as if it were skill.
# Rows with no resolvable actor (a schema predating this join, or an
# orphaned dataset row) are excluded on the same don't-guess principle
# the eval metrics use for actor 'unknown'.
TRAINING_ELIGIBLE_ACTORS = frozenset({"participant", "model"})


def is_training_eligible(actor: str | None) -> bool:
    return actor in TRAINING_ELIGIBLE_ACTORS


def build_sft_rows(rows: list[dict]) -> list[dict]:
    """Dataset rows (each a fen_legal_moves_to_move payload plus its
    move's "actor") to prompt/completion rows. A row is skipped, not
    guessed at, when it is missing a needed field or its actor is not
    training-eligible."""
    output = []
    for row in rows:
        if not is_training_eligible(row.get("actor")):
            continue
        fen = row.get("fen")
        legal_moves = row.get("legal_moves")
        target = row.get("target_uci")
        if not isinstance(fen, str) or not isinstance(legal_moves, list) or not target:
            continue
        output.append(
            {
                "prompt": PROMPT_TEMPLATE.format(fen=fen, legal_moves=", ".join(legal_moves)),
                "completion": json.dumps({"move": target}),
            }
        )
    return output


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
