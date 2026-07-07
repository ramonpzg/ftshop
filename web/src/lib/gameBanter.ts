/** One-liners for game events. Pure rotation, no randomness: the
 * caller keeps a counter, so tests stay deterministic and no two
 * consecutive events repeat a line. */

export const BANTER = {
  check: [
    "Check. Your king just got a strongly worded letter.",
    "Check. Someone skipped king safety day.",
    "Check, please. No, the king is paying.",
    "Check. The position is getting pin-teresting.",
    "Check. Rooks before feelings.",
  ],
  checkmate: [
    "Checkmate. The model sends its regards.",
    "Checkmate. That was a teachable moment. You were the dataset.",
    "Checkmate. Your king has left the building.",
    "Checkmate. Reward -1000, emotionally.",
  ],
  win: [
    "Checkmate. Somewhere a GPU is quietly sulking.",
    "Checkmate. The model would like to speak to its trainer. That is you.",
    "Checkmate. Put that game straight into the training set.",
    "Checkmate. Artificial intelligence, natural consequences.",
  ],
  loss: [
    "A loss is just a labeled example. Label: ouch.",
    "Logged. The dataset thanks you for your sacrifice.",
    "Filed under 'what not to do'. Valuable data, honestly.",
    "Loss recorded. Your future fine-tune will avenge this.",
  ],
} as const;

export type BanterKind = keyof typeof BANTER;

export function pickBanter(kind: BanterKind, index: number): string {
  const pool = BANTER[kind];
  return pool[((index % pool.length) + pool.length) % pool.length];
}
