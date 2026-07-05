/** Pure text formatting helpers. No I/O. */

export function metricLabel(metric: string): string {
  return metric
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

export function formatMetricValue(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}
