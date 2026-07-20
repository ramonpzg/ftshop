/** The six dataset encodings of one move, as the deck presents them.
 *
 * Values mirror the accepted contract in docs/datasets.md and the
 * phase 33 corrections: the board-tensor class for e2e4 is 3980 under
 * the from*320 + to*5 + promo vocabulary, and the policy shape is
 * policy_move_reward with the FEN included.
 *
 * Every payload is strictly valid JSON; a test parses each one.
 * Truncations are stated in the point line, never as bare `...`
 * inside the payload.
 */

export interface DatasetShape {
  name: string;
  payload: string;
  point: string;
}

const START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
const AFTER_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1";

export const DATASET_SHAPES: DatasetShape[] = [
  {
    name: "PGN prefix to move",
    payload: `{"prefix": "", "target_san": "e4"}`,
    point: "The model learns to continue a game script.",
  },
  {
    name: "FEN to move",
    payload: `{"fen": "${START}",
 "target_uci": "e2e4"}`,
    point: "The model learns positions, not histories.",
  },
  {
    name: "FEN + legal moves to move",
    payload: `{"fen": "${START}",
 "legal_moves": ["a2a3", "a2a4", "b2b3"],
 "target_uci": "e2e4"}`,
    point:
      "First three of the twenty legal moves shown. The environment does the rules; the model does the choosing.",
  },
  {
    name: "Board tensor to move class",
    payload: `{"tensor_shape": [8, 8, 12],
 "move_class": 3980, "uci": "e2e4"}`,
    point: "No language at all. 3980 = e2(12)*320 + e4(28)*5; the class inverts back to the move.",
  },
  {
    name: "Policy + move reward",
    payload: `{"fen": "${START}",
 "policy_target": {"e2e4": 1.0},
 "move_reward": 1}`,
    point:
      "One-hot on the move played. The reward scores the move, not the position; who is winning would need the game outcome or an engine.",
  },
  {
    name: "RL trajectory",
    payload: `{"state_fen": "${START}",
 "action_uci": "e2e4", "reward": 1,
 "next_state_fen": "${AFTER_E4}",
 "done": false}`,
    point: "State, action, reward. The gym formulation.",
  },
];
