import { formatMetricValue, metricLabel } from "../../calculations/formatting";
import type { EvalResult } from "../../data/api";
import "./EvalPanel.css";

interface EvalPanelProps {
  results: EvalResult[];
}

export function EvalPanel({ results }: EvalPanelProps) {
  if (results.length === 0) {
    return <p className="eval-panel-empty">No eval results yet.</p>;
  }

  return (
    <ul className="eval-panel" data-testid="eval-panel">
      {results.map((result) => (
        <li key={result.id} className="eval-row" title={result.definition ?? undefined}>
          <span className="eval-metric">{metricLabel(result.metric)}</span>
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
