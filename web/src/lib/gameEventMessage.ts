/** Factual labels for chess events shown under the board. */
export const GAME_EVENT_MESSAGES = {
  check: "Check.",
  checkmate: "Checkmate. The model won.",
  win: "Checkmate. You won.",
  loss: "Loss recorded.",
} as const;

export type GameEventKind = keyof typeof GAME_EVENT_MESSAGES;

export function gameEventMessage(kind: GameEventKind): string {
  return GAME_EVENT_MESSAGES[kind];
}
