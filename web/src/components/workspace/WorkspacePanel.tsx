import {
  CaretDown,
  CaretUp,
  ChartBar,
  ChatText,
  Code,
  Database,
  Horse,
  Package,
  Sliders,
} from "@phosphor-icons/react";
import { type ReactNode, useEffect, useState } from "react";
import { ArtifactPanel } from "../../components/artifact/ArtifactPanel";
import { ChessBoard } from "../../components/chess/ChessBoard";
import { DatasetPanel } from "../../components/chess/DatasetPanel";
import { ConfigPanel } from "../../components/config/ConfigPanel";
import { EvalPanel } from "../../components/eval/EvalPanel";
import { MiniIde } from "../../components/ide/MiniIde";
import {
  type Artifact,
  type Assessment,
  assessPosition,
  type DatasetExport,
  type DatasetRow,
  type EvalResult,
  exportTextDataset,
  fetchArtifacts,
  fetchEvals,
  fetchLlmStatus,
  fetchWorkspaceState,
  type LlmStatus,
  makeMove,
  modelMove,
  type MoveResponse,
  runJob,
  selectSnippet,
} from "../../data/api";
import { useCurrentUser } from "../../lib/currentUserContext";
import { usePresenterState } from "../../lib/presenterContext";
import type { WorkspaceShape } from "../tldraw/shapes/workspaceShapeTypes";
import "./WorkspacePanel.css";

interface WorkspacePanelProps {
  shape: WorkspaceShape;
  isEditing: boolean;
}

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

const TEXT_JOBS = [
  { jobType: "text.prompt_eval", label: "Run prompt eval" },
  { jobType: "text.reward_eval", label: "Run reward eval" },
];

interface SectionProps {
  id: string;
  title: string;
  tip: string;
  icon: ReactNode;
  isEditing: boolean;
  children: ReactNode;
}

/** A collapsible, scrollable block of the workspace. Collapsed state is a
 * per-browser preference, shared across workspaces. */
function Section({ id, title, tip, icon, isEditing, children }: SectionProps) {
  const storageKey = `euro-chess-studio:section-open:${id}`;
  const [open, setOpen] = useState(() => localStorage.getItem(storageKey) !== "0");

  function toggle() {
    const next = !open;
    setOpen(next);
    localStorage.setItem(storageKey, next ? "1" : "0");
  }

  return (
    <section className="workspace-panel-section" data-section={id} data-open={open}>
      <div className="workspace-section-header">
        <h3 title={tip}>
          {icon} {title}
        </h3>
        {isEditing && (
          <button
            type="button"
            className="workspace-section-toggle"
            onClick={toggle}
            title={open ? "Hide this section" : "Show this section"}
            data-testid={`section-toggle-${id}`}
          >
            {open ? <CaretUp size={11} /> : <CaretDown size={11} />}
          </button>
        )}
      </div>
      {open && <div className="workspace-section-body">{children}</div>}
    </section>
  );
}

export function WorkspacePanel({ shape, isEditing }: WorkspacePanelProps) {
  const currentUser = useCurrentUser();
  const { locked, resetToken } = usePresenterState();
  const isOwnWorkspace = currentUser?.id === shape.props.userId;
  const { workspaceId } = shape.props;

  const [fen, setFen] = useState(STARTING_FEN);
  const [datasetRows, setDatasetRows] = useState<DatasetRow[]>([]);
  const [selectedSnippetId, setSelectedSnippetId] = useState<string | null>(null);
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [evalResults, setEvalResults] = useState<EvalResult[]>([]);
  const [runningJob, setRunningJob] = useState(false);
  const [movePending, setMovePending] = useState(false);
  const [lastMove, setLastMove] = useState<{
    label: string;
    legal: boolean;
    reward: number;
  } | null>(null);
  const [llm, setLlm] = useState<LlmStatus | null>(null);
  const [vsModel, setVsModel] = useState(false);
  const [modelThinking, setModelThinking] = useState(false);
  const [analysis, setAnalysis] = useState<Assessment | null>(null);
  const [analysisState, setAnalysisState] = useState<"idle" | "loading" | "error">("idle");
  const [lastExport, setLastExport] = useState<DatasetExport | null>(null);

  // biome-ignore lint/correctness/useExhaustiveDependencies: resetToken is a manual refetch trigger, not read in the body
  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;
    fetchWorkspaceState(workspaceId).then((state) => {
      if (cancelled) return;
      setFen(state.workspace.board_fen);
      setDatasetRows(state.dataset_rows);
      setSelectedSnippetId(state.workspace.selected_snippet_id);
    });
    refreshArtifactAndEvals();
    return () => {
      cancelled = true;
    };
  }, [workspaceId, resetToken]);

  useEffect(() => {
    if (!isOwnWorkspace) return;
    let cancelled = false;
    fetchLlmStatus()
      .then((status) => {
        if (!cancelled) setLlm(status);
      })
      .catch(() => {
        if (!cancelled) setLlm(null);
      });
    return () => {
      cancelled = true;
    };
  }, [isOwnWorkspace]);

  function applyMoveResponse(response: MoveResponse, mover: "you" | "model") {
    const move = response.move;
    const label = move.san ?? move.uci;
    setLastMove({
      label: mover === "model" ? `Model: ${label}` : label,
      legal: move.is_legal,
      reward: move.reward,
    });
    if (move.is_legal) {
      setFen(move.fen_after);
    }
    setDatasetRows((prev) => [...prev, ...response.dataset_rows]);
    return move.is_legal;
  }

  async function refreshAnalysis() {
    setAnalysisState("loading");
    try {
      setAnalysis(await assessPosition(workspaceId));
      setAnalysisState("idle");
    } catch {
      setAnalysisState("error");
    }
  }

  async function triggerModelReply() {
    setModelThinking(true);
    try {
      const response = await modelMove(workspaceId);
      applyMoveResponse(response, "model");
    } catch {
      setLastMove({ label: "Model: no usable reply", legal: false, reward: 0 });
    } finally {
      setModelThinking(false);
    }
    void refreshAnalysis();
  }

  async function handleStartGame() {
    setVsModel(true);
    setLastMove(null);
    // If it's already the model's turn (black to move), kick it off now.
    if (fen.split(" ")[1] === "b") {
      await triggerModelReply();
    }
  }

  function refreshArtifactAndEvals() {
    fetchArtifacts({ modality: "text", workspaceId }).then((artifacts) => {
      setArtifact(artifacts[0] ?? null);
    });
    Promise.all([
      fetchEvals({ modality: "text", workspaceId }),
      fetchEvals({ modality: "text" }),
    ]).then(([computed, cached]) => {
      const cachedOnly = cached.filter((row) => row.workspace_id === null);
      setEvalResults([...computed, ...cachedOnly]);
    });
  }

  async function handleMove(uci: string) {
    if (movePending || modelThinking) return;
    setMovePending(true);
    let legal = false;
    try {
      // Illegal attempts stay visible: they earn reward -1, which is the
      // whole point of the RL framing.
      legal = applyMoveResponse(await makeMove(workspaceId, uci), "you");
    } finally {
      setMovePending(false);
    }
    if (legal && vsModel) {
      await triggerModelReply();
    }
  }

  async function handleSelectSnippet(snippetId: string) {
    setSelectedSnippetId(snippetId);
    await selectSnippet(workspaceId, snippetId);
  }

  async function handleRunJob(jobType: string) {
    setRunningJob(true);
    try {
      const response = await runJob(jobType, {}, workspaceId);
      setArtifact(response.artifact);
      refreshArtifactAndEvals();
    } finally {
      setRunningJob(false);
    }
  }

  const boardInteractive =
    isEditing && isOwnWorkspace && !locked && !movePending && !modelThinking;
  const llmReady = llm?.configured === true;
  const llmHint = llmReady
    ? `Play against ${llm?.model}. It answers every move.`
    : "Set OPENAI_API_KEY on the backend to enable the model opponent.";

  return (
    <div
      className={isOwnWorkspace ? "workspace-panel workspace-panel-own" : "workspace-panel"}
      data-testid={`workspace-panel-${shape.props.userId}`}
    >
      <header className="workspace-panel-header">
        <span>{shape.props.userName || "Unnamed"}</span>
        {!isOwnWorkspace && <span className="workspace-panel-readonly">view only</span>}
        {locked && <span className="workspace-panel-readonly">locked</span>}
        {!isEditing && <span className="workspace-panel-hint">Double-click to open</span>}
      </header>
      <div className="workspace-panel-columns">
        <div className="workspace-panel-col">
          <Section
            id="board"
            title="Board"
            tip="Play moves. python-chess validates every one on the server. Illegal attempts earn reward -1, which is the RL lesson."
            icon={<Horse size={12} weight="bold" />}
            isEditing={isEditing}
          >
            <ChessBoard fen={fen} interactive={boardInteractive} onMove={handleMove} />
            {isOwnWorkspace && isEditing && (
              <div className="workspace-game-controls">
                {vsModel ? (
                  <button type="button" onClick={() => setVsModel(false)}>
                    Stop game
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleStartGame}
                    disabled={!llmReady}
                    title={llmHint}
                    data-testid="start-game"
                  >
                    Start game
                  </button>
                )}
                {modelThinking && (
                  <span className="workspace-model-thinking">Model is thinking</span>
                )}
              </div>
            )}
            {lastMove && (
              <p
                className={
                  lastMove.legal ? "workspace-move-status" : "workspace-move-status move-illegal"
                }
                data-testid="move-status"
              >
                {lastMove.legal
                  ? `${lastMove.label}. Reward ${lastMove.reward > 0 ? "+" : ""}${lastMove.reward}`
                  : `Illegal: ${lastMove.label}. Reward ${lastMove.reward}`}
              </p>
            )}
          </Section>
          <Section
            id="config"
            title="Config"
            tip="Run jobs against your own game data. The backend decides how each job runs."
            icon={<Sliders size={12} weight="bold" />}
            isEditing={isEditing}
          >
            <ConfigPanel jobs={TEXT_JOBS} onRunJob={handleRunJob} running={runningJob} />
            <button
              type="button"
              className="workspace-export-button"
              data-testid="export-dataset"
              title="Writes every game's rows to data/processed/text/chess_sft.jsonl. The training snippets and the notebook load that exact file."
              onClick={async () => setLastExport(await exportTextDataset())}
            >
              Export dataset
            </button>
            {lastExport && (
              <p className="workspace-export-status" data-testid="export-status">
                {lastExport.file_name}. {lastExport.row_count} rows.{" "}
                <a href={`/api${lastExport.url}`} target="_blank" rel="noreferrer">
                  Open
                </a>
              </p>
            )}
          </Section>
          <Section
            id="eval"
            title="Eval"
            tip="Metrics from your actual moves (computed) next to illustrative ones that need heavier infra (cached)."
            icon={<ChartBar size={12} weight="bold" />}
            isEditing={isEditing}
          >
            <EvalPanel results={evalResults} />
          </Section>
        </div>
        <div className="workspace-panel-col">
          <Section
            id="dataset"
            title="Dataset"
            tip="Every move becomes training rows: PGN prefix, FEN to move, legal-moves context, board tensor, policy and value, RL trajectory."
            icon={<Database size={12} weight="bold" />}
            isEditing={isEditing}
          >
            <DatasetPanel rows={datasetRows} />
          </Section>
          <Section
            id="analysis"
            title="Analysis"
            tip="A model watches your game: position assessment plus the real-world scenario this game maps to."
            icon={<ChatText size={12} weight="bold" />}
            isEditing={isEditing}
          >
            <div className="workspace-analysis" data-testid="analysis-panel">
              {analysis ? (
                <>
                  <p className="workspace-analysis-text">{analysis.assessment}</p>
                  {analysis.real_world && (
                    <p className="workspace-analysis-real-world">{analysis.real_world}</p>
                  )}
                  <span className="workspace-analysis-model">{analysis.model}</span>
                </>
              ) : (
                <p className="workspace-analysis-empty">
                  {llmReady
                    ? "Play a move, get a read on the position and its real-world twin."
                    : "Set OPENAI_API_KEY on the backend to enable analysis."}
                </p>
              )}
              {analysisState === "loading" && (
                <p className="workspace-analysis-empty">Assessing position</p>
              )}
              {analysisState === "error" && (
                <p className="workspace-analysis-empty">Assessment failed. Next move retries.</p>
              )}
              {isOwnWorkspace && isEditing && llmReady && !vsModel && (
                <button type="button" className="workspace-assess-button" onClick={refreshAnalysis}>
                  Assess position
                </button>
              )}
            </div>
          </Section>
          <Section
            id="artifact"
            title="Artifact"
            tip="Job output lands here: eval payloads, generated files, cached reveals."
            icon={<Package size={12} weight="bold" />}
            isEditing={isEditing}
          >
            <ArtifactPanel artifact={artifact} />
          </Section>
        </div>
        <div className="workspace-panel-col workspace-panel-col-ide">
          <Section
            id="ide"
            title="Mini IDE"
            tip="The real code behind this page. Switch snippets with the tabs; this is what actually runs, not decoration."
            icon={<Code size={12} weight="bold" />}
            isEditing={isEditing}
          >
            <MiniIde selectedSnippetId={selectedSnippetId} onSelectSnippet={handleSelectSnippet} />
          </Section>
        </div>
      </div>
    </div>
  );
}
