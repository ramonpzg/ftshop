/** Pure text formatting helpers. No I/O. */

const ACRONYMS = new Set(["json", "fen", "pgn", "uci", "san", "rl", "sft"]);

export function metricLabel(metric: string): string {
  return metric
    .split("_")
    .map((word) =>
      ACRONYMS.has(word) ? word.toUpperCase() : word[0].toUpperCase() + word.slice(1),
    )
    .join(" ");
}

export function formatMetricValue(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

/** A signed delta with its sign always visible: "+0.42", "-0.75",
 * "0.00" for exact zero. The sign is the point; never drop it. */
export function formatDelta(delta: number): string {
  if (delta === 0) return "0.00";
  const magnitude = Math.abs(delta).toFixed(2);
  return delta > 0 ? `+${magnitude}` : `-${magnitude}`;
}
