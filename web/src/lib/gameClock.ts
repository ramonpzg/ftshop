/** Pure clock helpers for timed games. Mirrors the backend's rules:
 * one clock per match, default five minutes, thirty max. */

export const DEFAULT_TIME_LIMIT_SECONDS = 300;

export const TIME_LIMIT_CHOICES = [
  { seconds: 300, label: "5 min" },
  { seconds: 600, label: "10 min" },
  { seconds: 900, label: "15 min" },
  { seconds: 1800, label: "30 min" },
] as const;

/** "4:32" style countdown. Never goes below 0:00. */
export function formatClock(secondsLeft: number): string {
  const whole = Math.max(0, Math.ceil(secondsLeft));
  const minutes = Math.floor(whole / 60);
  const seconds = whole % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/** Breaking the news after a reload or server restart found the
 * clock already dead. */
export const EXPIRED_AWAY_NOTICE = "The clock ran out while you were away. That counts as a loss.";

/** One terse line per finished match, for the history list. */
export function describeMatch(game: {
  result: string;
  legal_moves: number;
  time_limit_seconds: number;
}): string {
  const labels: Record<string, string> = {
    loss_resign: "Loss, started over",
    loss_timeout: "Loss, time",
    loss: "Loss, checkmate",
    win: "Win, checkmate",
    draw: "Draw",
  };
  const label = labels[game.result] ?? game.result;
  const moves = game.legal_moves === 1 ? "1 move" : `${game.legal_moves} moves`;
  return `${label}. ${moves} on a ${Math.round(game.time_limit_seconds / 60)} min clock.`;
}

/** "google/gemma-4-2b-it" -> "gemma-4-2b-it": provider prefixes are
 * noise in a picker this small. */
export function modelShortName(modelId: string): string {
  const tail = modelId.split("/").pop();
  return tail || modelId;
}

/** Compact status word for the presenter dashboard. */
export function shortResult(result: string | null): string {
  if (result === null) return "playing";
  if (result === "win") return "win";
  if (result === "draw") return "draw";
  if (result.startsWith("loss")) return "loss";
  return result;
}

/** One line per way a game can end. Shown under the board. */
export function describeGameEnd(result: string): string {
  switch (result) {
    case "loss_resign":
      return "You started over. That is a loss.";
    case "loss_timeout":
      return "Time ran out. That is a loss.";
    case "win":
      return "Checkmate. You won.";
    case "loss":
      return "Checkmate. The model won.";
    case "draw":
      return "Stalemate. A draw.";
    default:
      return "Game over.";
  }
}
