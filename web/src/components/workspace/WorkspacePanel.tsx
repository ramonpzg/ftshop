import { useEffect, useState } from "react";
import { ChessBoard } from "../../components/chess/ChessBoard";
import { DatasetPanel } from "../../components/chess/DatasetPanel";
import { MiniIde } from "../../components/ide/MiniIde";
import { type DatasetRow, fetchWorkspaceState, makeMove, selectSnippet } from "../../data/api";
import { useCurrentUser } from "../../lib/currentUserContext";
import { usePresenterState } from "../../lib/presenterContext";
import type { WorkspaceShape } from "../tldraw/shapes/workspaceShapeTypes";
import "./WorkspacePanel.css";

interface WorkspacePanelProps {
  shape: WorkspaceShape;
  isEditing: boolean;
}

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

export function WorkspacePanel({ shape, isEditing }: WorkspacePanelProps) {
  const currentUser = useCurrentUser();
  const { locked, resetToken } = usePresenterState();
  const isOwnWorkspace = currentUser?.id === shape.props.userId;
  const { workspaceId } = shape.props;

  const [fen, setFen] = useState(STARTING_FEN);
  const [datasetRows, setDatasetRows] = useState<DatasetRow[]>([]);
  const [selectedSnippetId, setSelectedSnippetId] = useState<string | null>(null);

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
    return () => {
      cancelled = true;
    };
  }, [workspaceId, resetToken]);

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
          <h3>Board</h3>
          <ChessBoard fen={fen} interactive={boardInteractive} onMove={handleMove} />
        </section>
        <section className="workspace-panel-section" data-section="dataset">
          <h3>Dataset</h3>
          <DatasetPanel rows={datasetRows} />
        </section>
        <section className="workspace-panel-section" data-section="ide">
          <h3>Mini IDE</h3>
          <MiniIde selectedSnippetId={selectedSnippetId} onSelectSnippet={handleSelectSnippet} />
        </section>
        <section className="workspace-panel-section" data-section="config">
          <h3>Config</h3>
        </section>
        <section className="workspace-panel-section" data-section="artifact">
          <h3>Artifact</h3>
        </section>
        <section className="workspace-panel-section" data-section="eval">
          <h3>Eval</h3>
        </section>
      </div>
    </div>
  );
}
