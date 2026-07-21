import { ArrowsLeftRight, Cube, Database, Flask, Play } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { shortHash } from "../../calculations/adaptationView";
import { formatDelta, formatMetricValue, metricLabel } from "../../calculations/formatting";
import {
  type AdaptationState,
  apiErrorDetail,
  fetchAdaptationState,
  freezeDatasetSnapshot,
  runJob,
} from "../../data/api";
import { usePresenterState } from "../../lib/presenterContext";
import "./AdaptationPanel.css";

interface AdaptationPanelProps {
  isEditing: boolean;
  /** Poll cadence for the shared evidence; overridable in tests. */
  pollMs?: number;
}

// The browser stops waiting for a live run after this long; the server
// bounds the run itself (BENCHMARK_RUN_DEADLINE_SECONDS, max 300s).
const LIVE_RUN_WAIT_MS = 120_000;
// Aborting the browser request does NOT cancel the server run: it
// continues to its own deadline. Live controls stay locked until the
// run lands in the shared state or this generous ceiling (the server's
// maximum deadline clamp plus slack) passes with nothing to show,
// which means the run failed without producing a row.
const SERVER_RUN_MAX_MS = 330_000;
// The panel's state is the room's shared evidence, but tldraw sync
// carries none of it: without a poll, attendees would render whatever
// existed when their panel mounted, forever.
const SHARED_EVIDENCE_POLL_MS = 5_000;

interface LiveWait {
  startedAt: number;
  priorLiveRunIds: string[];
}

/** The presenter's vertical slice of the adaptation loop: freeze a
 * dataset, pick the config, replay the scripted training, benchmark
 * base and adapted checkpoints on one frozen suite, read the
 * comparison. Every step renders the backend's evidence; nothing here
 * invents state. Attendees see all of the evidence (kept fresh by a
 * single-flight poll); only the presenter client gets the controls,
 * and the backend additionally restricts paid live runs to the
 * presenter's machine and to one at a time. */
export function AdaptationPanel({
  isEditing,
  pollMs = SHARED_EVIDENCE_POLL_MS,
}: AdaptationPanelProps) {
  const { isPresenter } = usePresenterState();
  const [state, setState] = useState<AdaptationState | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [liveWait, setLiveWait] = useState<LiveWait | null>(null);
  const liveControllerRef = useRef<AbortController | null>(null);
  const refreshInFlightRef = useRef(false);

  const refresh = useCallback(async () => {
    // Single-flight: a slow response and a fast poll cadence must not
    // stack requests.
    if (refreshInFlightRef.current) return;
    refreshInFlightRef.current = true;
    try {
      const next = await fetchAdaptationState();
      setState(next);
      setLoadFailed(false);
    } catch {
      setLoadFailed(true);
    } finally {
      refreshInFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    void refresh();
    const interval = setInterval(() => void refresh(), pollMs);
    return () => clearInterval(interval);
  }, [refresh, pollMs]);

  // "Stop waiting" only aborts the browser's request; the server run
  // keeps going. The lock lifts when the run actually lands (the poll
  // brings it in) or when the server's own ceiling has passed with no
  // row, which means it failed. This local timer covers only the tab
  // that launched the run; reloads and other tabs get the same lock
  // from the server's in_progress record in the polled state, which is
  // also what refuses a duplicate run server-side (409) if a client
  // tries anyway.
  useEffect(() => {
    if (liveWait === null || state === null) return;
    const landed = state.runs.some(
      (run) => run.source === "live" && !liveWait.priorLiveRunIds.includes(run.id),
    );
    if (landed) {
      setLiveWait(null);
      setNotice("The live run landed; the run list below has it.");
    } else if (Date.now() - liveWait.startedAt > SERVER_RUN_MAX_MS) {
      setLiveWait(null);
      setNotice(
        "No live run landed within the server's maximum deadline; it " +
          "failed without producing a run. Check the backend log.",
      );
    }
  }, [state, liveWait]);

  async function act(name: string, run: () => Promise<unknown>) {
    setBusy(name);
    setNotice(null);
    try {
      await run();
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setNotice(
          "Stopped waiting in the browser. The server run continues to " +
            "its deadline; live controls stay locked until it lands or " +
            "times out.",
        );
      } else {
        // The backend's refusals are teaching material; show them as-is.
        setNotice(apiErrorDetail(error) ?? "The request failed.");
      }
    } finally {
      setBusy(null);
      void refresh();
    }
  }

  function runLiveBenchmark(suiteId: string) {
    setLiveWait({
      startedAt: Date.now(),
      priorLiveRunIds: (state?.runs ?? [])
        .filter((run) => run.source === "live")
        .map((run) => run.id),
    });
    return act("bench-live", () => {
      const controller = new AbortController();
      liveControllerRef.current = controller;
      const timeout = setTimeout(() => controller.abort(), LIVE_RUN_WAIT_MS);
      return runJob(
        "text.benchmark_eval",
        { suite_id: suiteId, checkpoint: "base", source: "live" },
        undefined,
        { signal: controller.signal },
      ).then(
        (result) => {
          // The server answered: the run is fully persisted (or the
          // request failed outright below). No zombie to wait for.
          setLiveWait(null);
          return result;
        },
        (error) => {
          const aborted = error instanceof DOMException && error.name === "AbortError";
          if (!aborted) setLiveWait(null);
          throw error;
        },
      ).finally(() => {
        clearTimeout(timeout);
        liveControllerRef.current = null;
      });
    });
  }

  if (!state) {
    // Only an initial load that never succeeded gets the empty failure
    // state; once evidence exists, a failed poll must not blank it.
    return loadFailed ? (
      <p className="adaptation-panel-empty" data-testid="adaptation-unavailable">
        Adaptation state unavailable. Backend down?
      </p>
    ) : (
      <p className="adaptation-panel-empty">Loading adaptation state.</p>
    );
  }

  // The server's in-flight record, not this tab's memory: a reloaded
  // panel or a second presenter tab locks live controls from here.
  const liveRunInFlight = liveWait !== null || state.live_benchmark.in_progress;

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
      <p className="adaptation-scripted-banner" data-testid="adaptation-scripted-banner">
        Scripted illustration: no model was trained. Training and replayed
        benchmarks replay authored fixtures. Only a live base run calls a
        real model.
      </p>
      {!isPresenter && (
        <p className="adaptation-presenter-note" data-testid="adaptation-presenter-note">
          The presenter runs these steps. Everything below is the room's
          shared evidence.
        </p>
      )}
      {loadFailed && (
        <p className="adaptation-notice" data-testid="adaptation-stale">
          Lost contact with the backend. Showing the last loaded
          evidence; retrying.
        </p>
      )}
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
          {isPresenter && (
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
          )}
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
          {isPresenter && (
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
                Scripted replay bound to the reference snapshot. No model is
                trained; live training is not part of the workshop build.
              </span>
            </div>
          )}
          {adapter && (
            <dl className="adaptation-card" data-testid="adapter-card">
              <div>
                <dt>Adapter</dt>
                <dd>
                  {adapter.checkpoint}{" "}
                  <span className="adaptation-badge" data-testid="adapter-source">
                    {adapter.result_source}
                  </span>
                  <span className="adaptation-scripted-tag"> scripted; no model was trained</span>
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
              {!suite.current_contract && (
                <p className="adaptation-notice" data-testid="suite-obsolete">
                  This suite was frozen under an older prompt contract (
                  {suite.prompt_version}) and no current-contract suite
                  exists. Restart the backend to reseed the current one.
                </p>
              )}
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
              {isPresenter && (
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
                  {state.live_benchmark.available &&
                    busy !== "bench-live" &&
                    !liveRunInFlight && (
                      <button
                        type="button"
                        onClick={() => runLiveBenchmark(suite.id)}
                        disabled={busy !== null}
                        data-testid="bench-base-live"
                      >
                        Run base live ({state.live_benchmark.model})
                      </button>
                    )}
                  {busy === "bench-live" && (
                    <button
                      type="button"
                      onClick={() => liveControllerRef.current?.abort()}
                      data-testid="bench-live-cancel"
                    >
                      Stop waiting
                    </button>
                  )}
                  {liveRunInFlight && busy !== "bench-live" && (
                    <span className="adaptation-source-note" data-testid="bench-live-waiting">
                      A live run is still in flight on the server; live
                      controls unlock when it lands or its deadline passes.
                    </span>
                  )}
                </div>
              )}
              {suiteRuns.length > 0 && (
                <ul className="adaptation-runs" data-testid="benchmark-runs">
                  {suiteRuns.map((run) => (
                    <li key={run.id}>
                      <span className="adaptation-run-checkpoint">{run.checkpoint}</span>
                      <span className="adaptation-badge">
                        {run.source === "replayed" ? "replayed (scripted)" : run.source}
                      </span>
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
        {comparison.base_run.checkpoint} ({sourceLabel(comparison.base_run.source)}) vs{" "}
        {comparison.adapted_run.checkpoint} ({sourceLabel(comparison.adapted_run.source)}) on{" "}
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

function sourceLabel(source: string): string {
  return source === "replayed" ? "replayed, scripted" : source;
}

function replySummary(reply: { parsed_move: string | null; is_legal: boolean | null } | null) {
  if (reply === null) return "no reply";
  if (reply.parsed_move === null) return "unusable reply";
  return `${reply.parsed_move} (${reply.is_legal ? "legal" : "illegal"})`;
}
