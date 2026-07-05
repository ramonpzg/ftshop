import { useCurrentUser } from "../../lib/currentUserContext";
import type { WorkspaceShape } from "../tldraw/shapes/workspaceShapeTypes";
import "./WorkspacePanel.css";

interface WorkspacePanelProps {
  shape: WorkspaceShape;
  isEditing: boolean;
}

const SECTIONS = [
  { key: "board", label: "Board" },
  { key: "dataset", label: "Dataset" },
  { key: "ide", label: "Mini IDE" },
  { key: "config", label: "Config" },
  { key: "artifact", label: "Artifact" },
  { key: "eval", label: "Eval" },
];

export function WorkspacePanel({ shape, isEditing }: WorkspacePanelProps) {
  const currentUser = useCurrentUser();
  const isOwnWorkspace = currentUser?.id === shape.props.userId;

  return (
    <div
      className={isOwnWorkspace ? "workspace-panel workspace-panel-own" : "workspace-panel"}
      data-testid={`workspace-panel-${shape.props.userId}`}
    >
      <header className="workspace-panel-header">
        <span>{shape.props.userName || "Unnamed"}</span>
        {!isOwnWorkspace && <span className="workspace-panel-readonly">view only</span>}
        {!isEditing && <span className="workspace-panel-hint">Double-click to open</span>}
      </header>
      <div className="workspace-panel-grid">
        {SECTIONS.map((section) => (
          <section key={section.key} className="workspace-panel-section" data-section={section.key}>
            <h3>{section.label}</h3>
          </section>
        ))}
      </div>
    </div>
  );
}
