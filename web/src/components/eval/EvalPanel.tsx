import { latestEvalResultsByScope } from "../../calculations/evalResults";
import { formatMetricValue, metricLabel } from "../../calculations/formatting";
import type { EvalResult } from "../../data/api";
import "./EvalPanel.css";

interface EvalPanelProps {
  results: EvalResult[];
}

function directionWords(direction: string | null): string | null {
  if (direction === "higher_is_better") return "higher is better";
  if (direction === "lower_is_better") return "lower is better";
  return direction;
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
        <li key={result.id} className="eval-row">
          <div className="eval-row-line">
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
          </div>
          {result.source === "cached" && result.note && (
            <span className="eval-note" data-testid={`eval-note-${result.metric}`}>
              {result.note}
            </span>
          )}
          <details className="eval-details" data-testid={`eval-details-${result.metric}`}>
            <summary>Definition and provenance</summary>
            <dl>
              {result.definition && (
                <div>
                  <dt>Definition</dt>
                  <dd>
                    {result.definition}
                    {result.version && ` (v${result.version})`}
                  </dd>
                </div>
              )}
              {result.unit && (
                <div>
                  <dt>Unit</dt>
                  <dd>{result.unit}</dd>
                </div>
              )}
              {result.direction && (
                <div>
                  <dt>Direction</dt>
                  <dd>{directionWords(result.direction)}</dd>
                </div>
              )}
              {result.denominator !== null && (
                <div>
                  <dt>Sample</dt>
                  <dd>{result.denominator} rows counted</dd>
                </div>
              )}
              {result.position_set_id && (
                <div>
                  <dt>Position set</dt>
                  <dd>{result.position_set_id}</dd>
                </div>
              )}
              <div>
                <dt>Source</dt>
                <dd>
                  {result.source === "cached"
                    ? "cached fixture, not a live computation"
                    : "computed from stored rows"}
                </dd>
              </div>
              <div>
                <dt>Run</dt>
                <dd>{result.created_at}</dd>
              </div>
              {result.note && result.source !== "cached" && (
                <div>
                  <dt>Note</dt>
                  <dd>{result.note}</dd>
                </div>
              )}
            </dl>
          </details>
        </li>
      ))}
    </ul>
  );
}
