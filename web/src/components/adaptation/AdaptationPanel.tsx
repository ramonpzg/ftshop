import { ArrowsLeftRight, Cube, Database, Flask, Play } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { shortHash } from "../../calculations/adaptationView";
import { formatDelta, formatMetricValue, metricLabel } from "../../calculations/formatting";
import {
  type AdaptationState,
  apiErrorDetail,
  fetchAdaptationState,
  freezeDatasetSnapshot,
  runJob,
} from "../../data/api";
import "./AdaptationPanel.css";

interface AdaptationPanelProps {
  isEditing: boolean;
}

/** The presenter's vertical slice of the adaptation loop: freeze a
 * dataset, pick the config, replay the training, benchmark base and
 * adapted checkpoints on one frozen suite, read the comparison. Every
 * step renders the backend's evidence; nothing here invents state. */
export function AdaptationPanel({ isEditing }: AdaptationPanelProps) {
  const [state, setState] = useState<AdaptationState | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(() => {
    fetchAdaptationState()
      .then((next) => {
        setState(next);
        setLoadFailed(false);
      })
      .catch(() => setLoadFailed(true));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function act(name: string, run: () => Promise<unknown>) {
    setBusy(name);
    setNotice(null);
    try {
      await run();
    } catch (error) {
      // The backend's refusals are teaching material; show them as-is.
      setNotice(apiErrorDetail(error) ?? "The request failed.");
    } finally {
      setBusy(null);
      refresh();
    }
  }

  if (loadFailed) {
    return <p className="adaptation-panel-empty">Adaptation state unavailable. Backend down?</p>;
  }
  if (!state) {
    return <p className="adaptation-panel-empty">Loading adaptation state.</p>;
  }

  const config = state.configs[0] ?? null;
  const suite = state.suites[0] ?? null;
  const snapshot =
    state.snapshots.find((s) => s.id === selectedSnapshotId) ??
    state.snapshots.find((s) => s.origin === "seeded") ??
    state.snapshots[0] ??
    null;
  const adapter = state.adapters[state.adapters.length - 1] ?? null;
  const comparison = state.comparison;
  const suiteRuns = suite ? state.runs.filter((run) => run.suite_id === suite.id) : [];

  return (
    <div className="adaptation-panel" data-testid="adaptation-panel">
      <header className="adaptation-panel-header">
        <span>Adaptation. Pairs in, adapter out, eval always.</span>
        {!isEditing && <span className="adaptation-panel-hint">Double-click to open</span>}
      </header>
      {notice && (
        <p className="adaptation-notice" data-testid="adaptation-notice">
          {notice}
        </p>
      )}
      <div className="adaptation-steps">
        <section className="adaptation-step" data-step="dataset">
          <h3>
            <Database size={13} weight="bold" /> 1. Dataset
          </h3>
          <div className="adaptation-controls">
            <select
              value={snapshot?.id ?? ""}
              onChange={(event) => setSelectedSnapshotId(event.target.value)}
              data-testid="snapshot-select"
            >
              {state.snapshots.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label} ({s.row_count} rows, {s.origin})
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => act("freeze", () => freezeDatasetSnapshot())}
              disabled={busy !== null}
              data-testid="freeze-snapshot"
            >
              Freeze room dataset
            </button>
          </div>
          {snapshot && (
            <dl className="adaptation-card" data-testid="snapshot-card">
              <div>
                <dt>Rows</dt>
                <dd>
                  {snapshot.row_count} eligible, {snapshot.excluded_ineligible_count} excluded
                  (fallback/unknown)
                </dd>
              </div>
              <div>
                <dt>Sources</dt>
                <dd>
                  {snapshot.source_game_count} games, {snapshot.source_workspace_count} workspaces
                </dd>
              </div>
              <div>
                <dt>Scenarios</dt>
                <dd>
                  {snapshot.scenario_raw_count} raw, {snapshot.scenario_approved_count} approved
                </dd>
              </div>
              <div>
                <dt>Schema</dt>
                <dd>{snapshot.schema_version}</dd>
              </div>
              <div>
                <dt>Content hash</dt>
                <dd data-testid="snapshot-hash">{shortHash(snapshot.content_hash)}</dd>
              </div>
              {snapshot.row_preview && snapshot.row_preview.length > 0 && (
                <details className="adaptation-disclosure">
                  <summary>Row preview</summary>
                  <pre>{JSON.stringify(snapshot.row_preview, null, 2)}</pre>
                </details>
              )}
            </dl>
          )}
        </section>

        <section className="adaptation-step" data-step="config">
          <h3>
            <Cube size={13} weight="bold" /> 2. Config
          </h3>
          {config ? (
            <dl className="adaptation-card" data-testid="config-card">
              <div>
                <dt>Base checkpoint</dt>
                <dd>{config.base_model}</dd>
              </div>
              <div>
                <dt>Method</dt>
                <dd>
                  {config.method} r={config.lora_r} alpha={config.lora_alpha} dropout=
                  {config.lora_dropout}
                </dd>
              </div>
              <div>
                <dt>Run</dt>
                <dd>
                  lr={config.learning_rate} epochs={config.epochs} batch={config.batch_size} seed=
                  {config.seed}
                </dd>
              </div>
              <div>
                <dt>Output task</dt>
                <dd>{config.output_task}</dd>
              </div>
              <div>
                <dt>Config hash</dt>
                <dd>{shortHash(config.config_hash)}</dd>
              </div>
              <details className="adaptation-disclosure">
                <summary>Model roles and limits</summary>
                <p>Training start: {config.base_model}</p>
                <p>Inference repo (GGUF): {config.inference_repo}</p>
                <p>Serving alias: {config.serving_alias}</p>
                <p>Adapted checkpoint label: {config.target_checkpoint}</p>
                <p>{config.limitations}</p>
              </details>
            </dl>
          ) : (
            <p className="adaptation-empty-line">No training config available.</p>
          )}
        </section>

        <section className="adaptation-step" data-step="train">
          <h3>
            <Play size={13} weight="bold" /> 3. Train
          </h3>
          <div className="adaptation-controls">
            <button
              type="button"
              onClick={() =>
                act("train", () =>
                  runJob("text.train_adapter", {
                    dataset_snapshot_id: snapshot?.id,
                    config_id: config?.config_id,
                  }),
                )
              }
              disabled={busy !== null || !snapshot || !config}
              data-testid="train-adapter"
            >
              {busy === "train" ? "Training..." : "Train adapter"}
            </button>
            <span className="adaptation-source-note">
              Cached replay bound to the reference snapshot. Live training is not part of the
              workshop build.
            </span>
          </div>
          {adapter && (
            <dl className="adaptation-card" data-testid="adapter-card">
              <div>
                <dt>Adapter</dt>
                <dd>
                  {adapter.checkpoint}{" "}
                  <span className="adaptation-badge" data-testid="adapter-source">
                    {adapter.result_source}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Base</dt>
                <dd>{adapter.base_model}</dd>
              </div>
              <div>
                <dt>Dataset hash</dt>
                <dd data-testid="adapter-dataset-hash">
                  {shortHash(adapter.dataset_content_hash)}
                </dd>
              </div>
              <div>
                <dt>Config hash</dt>
                <dd>{shortHash(adapter.config_hash)}</dd>
              </div>
              <div>
                <dt>Runner</dt>
                <dd>{adapter.runner}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{adapter.created_at}</dd>
              </div>
              <details className="adaptation-disclosure">
                <summary>Limitations</summary>
                <p>{adapter.limitations}</p>
              </details>
            </dl>
          )}
        </section>

        <section className="adaptation-step" data-step="benchmark">
          <h3>
            <Flask size={13} weight="bold" /> 4. Benchmark
          </h3>
          {suite ? (
            <>
              <dl className="adaptation-card" data-testid="suite-card">
                <div>
                  <dt>Suite</dt>
                  <dd>
                    {suite.label}: {suite.example_count} frozen examples
                  </dd>
                </div>
                <div>
                  <dt>Prompt contract</dt>
                  <dd>{suite.prompt_version}</dd>
                </div>
                <div>
                  <dt>Content hash</dt>
                  <dd>{shortHash(suite.content_hash)}</dd>
                </div>
                <div>
                  <dt>Position set</dt>
                  <dd data-testid="suite-psid">{shortHash(suite.position_set_id)}</dd>
                </div>
                <details className="adaptation-disclosure">
                  <summary>Examples</summary>
                  {suite.note && <p>{suite.note}</p>}
                  <ul>
                    {suite.examples.map((example) => (
                      <li key={example.example_id}>
                        {example.example_id}: {example.fen}
                      </li>
                    ))}
                  </ul>
                </details>
              </dl>
              <div className="adaptation-controls">
                <button
                  type="button"
                  onClick={() =>
                    act("bench-base", () =>
                      runJob("text.benchmark_eval", {
                        suite_id: suite.id,
                        checkpoint: "base",
                        source: "replayed",
                      }),
                    )
                  }
                  disabled={busy !== null}
                  data-testid="bench-base"
                >
                  Run base (replayed)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    act("bench-adapted", () =>
                      runJob("text.benchmark_eval", {
                        suite_id: suite.id,
                        checkpoint: config?.target_checkpoint ?? "gemma-chess-sft-v1",
                        source: "replayed",
                      }),
                    )
                  }
                  disabled={busy !== null}
                  data-testid="bench-adapted"
                >
                  Run adapted (replayed)
                </button>
                {state.live_benchmark.available && (
                  <button
                    type="button"
                    onClick={() =>
                      act("bench-live", () =>
                        runJob("text.benchmark_eval", {
                          suite_id: suite.id,
                          checkpoint: "base",
                          source: "live",
                        }),
                      )
                    }
                    disabled={busy !== null}
                    data-testid="bench-base-live"
                  >
                    Run base live ({state.live_benchmark.model})
                  </button>
                )}
              </div>
              {suiteRuns.length > 0 && (
                <ul className="adaptation-runs" data-testid="benchmark-runs">
                  {suiteRuns.map((run) => (
                    <li key={run.id}>
                      <span className="adaptation-run-checkpoint">{run.checkpoint}</span>
                      <span className="adaptation-badge">{run.source}</span>
                      <span>{run.model}</span>
                      <span>
                        {run.reply_count}/{run.example_count} replies
                        {run.transport_failed_count > 0 && `, ${run.transport_failed_count} failed`}
                      </span>
                      <span data-testid={`run-psid-${run.id}`}>
                        {run.position_set_id === null
                          ? "no position set"
                          : run.position_set_id === suite.position_set_id
                            ? "position set matches suite"
                            : "position set differs from suite"}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p className="adaptation-empty-line">No evaluation suite seeded.</p>
          )}
        </section>

        <section className="adaptation-step" data-step="compare">
          <h3>
            <ArrowsLeftRight size={13} weight="bold" /> 5. Compare
          </h3>
          {comparison ? (
            <ComparisonView comparison={comparison} />
          ) : (
            <p className="adaptation-empty-line" data-testid="comparison-empty">
              Run a base and an adapted benchmark on the same suite to compare.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}

function ComparisonView({
  comparison,
}: {
  comparison: NonNullable<AdaptationState["comparison"]>;
}) {
  return (
    <div data-testid="comparison">
      <p className="adaptation-comparison-runs">
        {comparison.base_run.checkpoint} ({comparison.base_run.source}) vs{" "}
        {comparison.adapted_run.checkpoint} ({comparison.adapted_run.source}) on{" "}
        {comparison.suite_label}
      </p>
      {!comparison.comparable && (
        <p className="adaptation-notice" data-testid="comparison-not-comparable">
          Not comparable: {comparison.reasons.join("; ")}
        </p>
      )}
      <table className="adaptation-metrics" data-testid="comparison-metrics">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Base</th>
            <th>Adapted</th>
            <th>Delta</th>
          </tr>
        </thead>
        <tbody>
          {comparison.metrics.map((metric) => (
            <tr key={metric.metric} data-verdict={metric.verdict ?? "none"}>
              <td>
                {metricLabel(metric.metric)}
                {metric.direction === "lower_is_better" && (
                  <span className="adaptation-direction"> (lower is better)</span>
                )}
              </td>
              <td>
                {metric.base_value !== null ? formatMetricValue(metric.base_value) : "-"}
                {metric.base_numerator !== null && metric.base_denominator !== null && (
                  <span className="adaptation-count">
                    {" "}
                    {metric.base_numerator}/{metric.base_denominator}
                  </span>
                )}
              </td>
              <td>
                {metric.adapted_value !== null ? formatMetricValue(metric.adapted_value) : "-"}
                {metric.adapted_numerator !== null && metric.adapted_denominator !== null && (
                  <span className="adaptation-count">
                    {" "}
                    {metric.adapted_numerator}/{metric.adapted_denominator}
                  </span>
                )}
              </td>
              <td data-testid={`delta-${metric.metric}`}>
                {metric.comparable && metric.delta !== null
                  ? `${formatDelta(metric.delta)} ${metric.verdict}`
                  : `Not comparable: ${metric.reason}`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <details className="adaptation-disclosure">
        <summary>Examples ({comparison.examples.length})</summary>
        <ul className="adaptation-examples" data-testid="comparison-examples">
          {comparison.examples.map((example) => (
            <li key={example.example_id}>
              <span className="adaptation-example-id">{example.example_id}</span>
              <span>
                base: {replySummary(example.base)} | adapted: {replySummary(example.adapted)}
              </span>
              <details>
                <summary>Raw</summary>
                <p className="adaptation-example-prompt">{example.prompt}</p>
                <p>base ({example.base?.reply_source ?? "missing"}):</p>
                <pre>{example.base?.raw_response ?? "(no reply)"}</pre>
                <p>adapted ({example.adapted?.reply_source ?? "missing"}):</p>
                <pre>{example.adapted?.raw_response ?? "(no reply)"}</pre>
              </details>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}

function replySummary(reply: { parsed_move: string | null; is_legal: boolean | null } | null) {
  if (reply === null) return "no reply";
  if (reply.parsed_move === null) return "unusable reply";
  return `${reply.parsed_move} (${reply.is_legal ? "legal" : "illegal"})`;
}
