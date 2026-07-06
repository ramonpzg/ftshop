import { ChartBar, Code, Database, Horse, Package, Sliders } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { ArtifactPanel } from "../../components/artifact/ArtifactPanel";
import { ChessBoard } from "../../components/chess/ChessBoard";
import { DatasetPanel } from "../../components/chess/DatasetPanel";
import { ConfigPanel } from "../../components/config/ConfigPanel";
import { EvalPanel } from "../../components/eval/EvalPanel";
import { MiniIde } from "../../components/ide/MiniIde";
import {
  type Artifact,
  type DatasetRow,
  type EvalResult,
  fetchArtifacts,
  fetchEvals,
  fetchWorkspaceState,
  makeMove,
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
    const response = await makeMove(workspaceId, uci);
    if (response.move.is_legal) {
      setFen(response.move.fen_after);
      setDatasetRows((prev) => [...prev, ...response.dataset_rows]);
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

  const boardInteractive = isEditing && isOwnWorkspace && !locked;

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
      <div className="workspace-panel-grid">
        <section className="workspace-panel-section" data-section="board">
          <h3>
            <Horse size={12} weight="bold" /> Board
          </h3>
          <ChessBoard fen={fen} interactive={boardInteractive} onMove={handleMove} />
        </section>
        <section className="workspace-panel-section" data-section="dataset">
          <h3>
            <Database size={12} weight="bold" /> Dataset
          </h3>
          <DatasetPanel rows={datasetRows} />
        </section>
        <section className="workspace-panel-section" data-section="ide">
          <h3>
            <Code size={12} weight="bold" /> Mini IDE
          </h3>
          <MiniIde selectedSnippetId={selectedSnippetId} onSelectSnippet={handleSelectSnippet} />
        </section>
        <section className="workspace-panel-section" data-section="config">
          <h3>
            <Sliders size={12} weight="bold" /> Config
          </h3>
          <ConfigPanel jobs={TEXT_JOBS} onRunJob={handleRunJob} running={runningJob} />
        </section>
        <section className="workspace-panel-section" data-section="artifact">
          <h3>
            <Package size={12} weight="bold" /> Artifact
          </h3>
          <ArtifactPanel artifact={artifact} />
        </section>
        <section className="workspace-panel-section" data-section="eval">
          <h3>
            <ChartBar size={12} weight="bold" /> Eval
          </h3>
          <EvalPanel results={evalResults} />
        </section>
      </div>
    </div>
  );
}
