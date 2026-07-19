import { Copy } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import {
  apiErrorDetail,
  assessPosition,
  fetchScenario,
  reviewScenario,
  type Scenario,
} from "../../data/api";

interface ScenarioSectionProps {
  workspaceId: string;
  llmReady: boolean;
  /** Whether this browser may act: own workspace, editing, not locked. */
  canAct: boolean;
  /** Incremented after each applied model turn to request a fresh read. */
  refreshKey: number;
}

/** The persisted real-world scenario mapping: suggestion, review, and
 * recovery. Persistence lives on the backend; this component only calls
 * the API and renders what came back. */
export function ScenarioSection({
  workspaceId,
  llmReady,
  canAct,
  refreshKey,
}: ScenarioSectionProps) {
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ assessment: "", real_world: "", video_prompt: "" });

  // Reload restores the prior persisted mapping.
  useEffect(() => {
    let cancelled = false;
    fetchScenario(workspaceId)
      .then((restored) => {
        if (!cancelled && restored) setScenario(restored);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  // A fresh suggestion after each applied model turn, same cadence as
  // before persistence existed.
  // biome-ignore lint/correctness/useExhaustiveDependencies: refreshKey is the trigger; suggest is stable per render
  useEffect(() => {
    if (refreshKey > 0) void suggest();
  }, [refreshKey]);

  async function suggest() {
    setState("loading");
    setEditing(false);
    try {
      setScenario(await assessPosition(workspaceId));
      setState("idle");
      setError(null);
    } catch (requestError) {
      setState("error");
      setError(apiErrorDetail(requestError));
    }
  }

  async function accept() {
    if (!scenario) return;
    setScenario(await reviewScenario(scenario.id, { accept: true }).catch(() => scenario));
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
    } catch (requestError) {
      setError(apiErrorDetail(requestError));
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
      ) : (
        <p className="workspace-analysis-empty">
          {llmReady
            ? "Play a move, get a read on the position and its real-world twin."
            : "Set OPENAI_API_KEY on the backend to enable analysis."}
        </p>
      )}
      {state === "loading" && <p className="workspace-analysis-empty">Assessing position</p>}
      {state === "error" && (
        <p className="workspace-analysis-empty" data-testid="scenario-error">
          Assessment failed{error ? `: ${error.slice(0, 160)}` : ""}. The last saved mapping is
          untouched.
        </p>
      )}
      {canAct && llmReady && state !== "loading" && (
        <button
          type="button"
          className="workspace-assess-button"
          onClick={() => void suggest()}
          data-testid="assess-position"
        >
          {state === "error" ? "Retry assessment" : "Assess position"}
        </button>
      )}
    </div>
  );
}
