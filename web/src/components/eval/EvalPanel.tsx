import { latestEvalResultsByScope } from "../../calculations/evalResults";
import { formatMetricValue, metricLabel } from "../../calculations/formatting";
import type { EvalResult } from "../../data/api";
import "./EvalPanel.css";

interface EvalPanelProps {
  results: EvalResult[];
}

function provenanceTitle(result: EvalResult): string {
  return [
    result.definition,
    result.model ? `model: ${result.model}` : null,
    result.checkpoint ? `checkpoint: ${result.checkpoint}` : null,
    `run: ${result.created_at}`,
  ]
    .filter(Boolean)
    .join(" | ");
}

export function EvalPanel({ results }: EvalPanelProps) {
  // The backend keeps every re-run's row (a growing move history means
  // a genuinely different position set each time); the live panel only
  // needs the current state of each metric, not its whole history.
  const latest = latestEvalResultsByScope(results);

  if (latest.length === 0) {
    return <p className="eval-panel-empty">No eval results yet.</p>;
  }

  return (
    <ul className="eval-panel" data-testid="eval-panel">
      {latest.map((result) => (
        <li key={result.id} className="eval-row" title={provenanceTitle(result)}>
          <span className="eval-metric">{metricLabel(result.metric)}</span>
          {(result.model || result.checkpoint) && (
            <span className="eval-scope" data-testid={`eval-scope-${result.metric}`}>
              {[result.model, result.checkpoint].filter(Boolean).join(" ")}
            </span>
          )}
          <span className="eval-value">{formatMetricValue(result.value)}</span>
          {result.numerator !== null && result.denominator !== null && (
            <span className="eval-count" data-testid={`eval-count-${result.metric}`}>
              {result.numerator}/{result.denominator}
            </span>
          )}
          <span className={`eval-source eval-source-${result.source}`}>{result.source}</span>
          {result.source === "cached" && result.note && (
            <span className="eval-note" data-testid={`eval-note-${result.metric}`}>
              {result.note}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}
