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
