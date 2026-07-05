/** Real, runnable snippets shown in the mini IDE. Each mirrors the actual
 * backend logic it's teaching, trimmed to something readable standalone. */

export interface Snippet {
  id: string;
  label: string;
  code: string;
}

export const SNIPPETS: Snippet[] = [
  {
    id: "prompt_template",
    label: "Prompt template",
    code: `PROMPT_TEMPLATE = """You are a chess engine assistant.

Position (FEN): {fen}
Legal moves (UCI): {legal_moves}

Return exactly one move from the legal moves list, in UCI format.
Respond with JSON: {{"move": "<uci>"}}
"""


def build_prompt(fen: str, legal_moves: list[str]) -> str:
    return PROMPT_TEMPLATE.format(fen=fen, legal_moves=", ".join(legal_moves))


# build_prompt(chess.STARTING_FEN, ["e2e4", "d2d4", "g1f3", ...])
`,
  },
  {
    id: "legal_move_validation",
    label: "Legal move validation",
    code: `import chess


def is_legal_move(fen: str, uci: str) -> bool:
    board = chess.Board(fen)
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        return False
    return move in board.legal_moves


fen = chess.STARTING_FEN
print(is_legal_move(fen, "e2e4"))  # True
print(is_legal_move(fen, "e2e5"))  # False, pawns don't jump two ranks from e2 to e5
`,
  },
  {
    id: "dataset_row_builder",
    label: "Dataset row builder",
    code: `import chess


def build_fen_to_move_row(fen_before: str, uci: str) -> dict:
    board = chess.Board(fen_before)
    move = chess.Move.from_uci(uci)
    san = board.san(move)
    return {
        "shape": "fen_to_move",
        "payload": {"fen": fen_before, "target_uci": uci, "target_san": san},
    }


row = build_fen_to_move_row(chess.STARTING_FEN, "e2e4")
print(row)
# {"shape": "fen_to_move", "payload": {"fen": "...", "target_uci": "e2e4", "target_san": "e4"}}
`,
  },
  {
    id: "reward_function",
    label: "RL reward function",
    code: `def compute_reward(*, legal: bool, is_check: bool, is_checkmate: bool) -> int:
    if not legal:
        return -1
    if is_checkmate:
        return 10
    if is_check:
        return 2
    return 1


# SFT teaches the model what good answers look like.
# RL teaches the model what good actions do -- this reward is what RL needs,
# and chess is a good RL environment because the environment can validate
# every move for you.
`,
  },
];

export function getSnippetById(id: string): Snippet {
  const snippet = SNIPPETS.find((s) => s.id === id);
  if (!snippet) throw new Error(`unknown snippet id: ${id}`);
  return snippet;
}
