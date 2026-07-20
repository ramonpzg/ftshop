import { Copy } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import {
  apiErrorDetail,
  assessPosition,
  fetchScenario,
  reviewScenario,
  type Scenario,
} from "../../data/api";
import { usePresenterState } from "../../lib/presenterContext";

interface ScenarioSectionProps {
  workspaceId: string;
  llmReady: boolean;
  /** Whether this browser may act: own workspace, editing, not locked. */
  canAct: boolean;
}

/** The persisted real-world scenario mapping: suggestion, review, and
 * recovery. Persistence lives on the backend; this component only calls
 * the API and renders what came back.
 *
 * Generation is manual and presenter-only (the room model policy: an
 * assessment is a scenario-model call, and it used to fire after every
 * model turn in forty browsers at once; the backend enforces the same
 * rule with a 403). Reviewing a landed mapping stays open to whoever
 * owns the workspace. */
export function ScenarioSection({ workspaceId, llmReady, canAct }: ScenarioSectionProps) {
  const { isPresenter } = usePresenterState();
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  // Which action failed, so the message and the recovery button match
  // what actually went wrong: a failed review should not offer a
  // button labelled "Retry assessment" (it would start a fresh
  // suggestion, not retry saving the review).
  const [errorSource, setErrorSource] = useState<"assessment" | "review" | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ assessment: "", real_world: "", video_prompt: "" });

  // Reload restores the same combination a live failure already shows
  // on screen: the last mapping that actually succeeded stays visible
  // (latest_success), and a more recent failure is surfaced alongside
  // it (latest) rather than replacing it. Returning only `latest` would
  // make a still-good mapping unreachable the moment the page
  // refreshes after a later failure.
  useEffect(() => {
    let cancelled = false;
    fetchScenario(workspaceId)
      .then((restored) => {
        if (cancelled) return;
        if (restored.latest_success) setScenario(restored.latest_success);
        if (restored.latest?.status === "failed") {
          setState("error");
          setError(restored.latest.error_detail);
          setErrorSource("assessment");
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  async function suggest() {
    setState("loading");
    setEditing(false);
    try {
      setScenario(await assessPosition(workspaceId));
      setState("idle");
      setError(null);
      setErrorSource(null);
    } catch (requestError) {
      setState("error");
      setError(apiErrorDetail(requestError));
      setErrorSource("assessment");
    }
  }

  async function accept() {
    if (!scenario) return;
    try {
      setScenario(await reviewScenario(scenario.id, { accept: true }));
    } catch (requestError) {
      setState("error");
      setError(apiErrorDetail(requestError));
      setErrorSource("review");
    }
  }

  function startEdit() {
    if (!scenario) return;
    setDraft({
      assessment: scenario.assessment ?? "",
      real_world: scenario.real_world ?? "",
      video_prompt: scenario.video_prompt ?? "",
    });
    setEditing(true);
  }

  async function saveEdit() {
    if (!scenario) return;
    try {
      setScenario(await reviewScenario(scenario.id, { accept: false, ...draft }));
      setEditing(false);
      setState("idle");
      setError(null);
      setErrorSource(null);
    } catch (requestError) {
      // Stay in the edit form (the draft is not lost) but surface the
      // failure: setting only `error` without `state` left this
      // silent, since the error message only renders when state is
      // "error".
      setState("error");
      setError(apiErrorDetail(requestError));
      setErrorSource("review");
    }
  }

  return (
    <div className="workspace-analysis" data-testid="analysis-panel">
      {scenario ? (
        editing ? (
          <div className="workspace-scenario-edit" data-testid="scenario-edit">
            <textarea
              value={draft.assessment}
              onChange={(event) => setDraft({ ...draft, assessment: event.target.value })}
              aria-label="Assessment"
              rows={2}
            />
            <textarea
              value={draft.real_world}
              onChange={(event) => setDraft({ ...draft, real_world: event.target.value })}
              aria-label="Real-world mapping"
              rows={3}
            />
            <textarea
              value={draft.video_prompt}
              onChange={(event) => setDraft({ ...draft, video_prompt: event.target.value })}
              aria-label="Video prompt"
              rows={4}
            />
            <div className="workspace-scenario-actions">
              <button type="button" onClick={saveEdit} data-testid="scenario-save-edit">
                Save edit
              </button>
              <button
                type="button"
                className="workspace-button-quiet"
                onClick={() => setEditing(false)}
              >
                Discard
              </button>
            </div>
          </div>
        ) : (
          <>
            <p className="workspace-analysis-text">{scenario.assessment}</p>
            {scenario.real_world && (
              <p className="workspace-analysis-real-world">{scenario.real_world}</p>
            )}
            {scenario.video_prompt && (
              <div className="workspace-analysis-video-prompt">
                <p>{scenario.video_prompt}</p>
                <button
                  type="button"
                  onClick={() => void navigator.clipboard.writeText(scenario.video_prompt ?? "")}
                  title="Copy video prompt"
                  aria-label="Copy video prompt"
                >
                  <Copy size={12} />
                </button>
              </div>
            )}
            <span className="workspace-analysis-model" data-testid="scenario-provenance">
              {scenario.model} {scenario.prompt_version} <em>{scenario.status}</em>
            </span>
            {canAct && scenario.status === "suggested" && (
              <div className="workspace-scenario-actions">
                <button type="button" onClick={accept} data-testid="scenario-accept">
                  Accept
                </button>
                <button type="button" onClick={startEdit} data-testid="scenario-start-edit">
                  Edit
                </button>
              </div>
            )}
          </>
        )
      ) : state === "error" ? null : (
        // Suppressed while an error is showing: "play a move to get a
        // read" next to "assessment failed" would wrongly imply nothing
        // had been attempted yet.
        <p className="workspace-analysis-empty">
          {!llmReady
            ? "Set OPENAI_API_KEY on the backend to enable analysis."
            : isPresenter
              ? "Assess a position to map it to a real-world scenario."
              : "Scenario reads are presenter-run. When one lands here, review it."}
        </p>
      )}
      {state === "loading" && <p className="workspace-analysis-empty">Assessing position</p>}
      {state === "error" && (
        <p className="workspace-analysis-empty" data-testid="scenario-error">
          {errorSource === "review"
            ? `Could not save your review${error ? `: ${error.slice(0, 160)}` : ""}.`
            : `Assessment failed${error ? `: ${error.slice(0, 160)}` : ""}.`}{" "}
          The last saved mapping is untouched.
        </p>
      )}
      {canAct && llmReady && isPresenter && state !== "loading" && (
        <button
          type="button"
          className="workspace-assess-button"
          onClick={() => void suggest()}
          data-testid="assess-position"
        >
          {state === "error" && errorSource === "assessment"
            ? "Retry assessment"
            : "Assess position"}
        </button>
      )}
    </div>
  );
}
