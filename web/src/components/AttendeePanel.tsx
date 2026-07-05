import { useEffect, useState } from "react";
import type { Editor } from "tldraw";
import { ensureWorkspaceShape } from "../actions/ensureWorkspaceShape";
import { navigateToWorkspace } from "../actions/navigateToWorkspace";
import { fetchWorkspaces, type WorkspaceWithDetails } from "../data/api";
import "./AttendeePanel.css";

interface AttendeePanelProps {
  editor: Editor | null;
  currentUserId: string | null;
  refreshToken: number;
}

export function AttendeePanel({ editor, currentUserId, refreshToken }: AttendeePanelProps) {
  const [workspaces, setWorkspaces] = useState<WorkspaceWithDetails[]>([]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: refreshToken is a manual refetch trigger, not read in the body
  useEffect(() => {
    let cancelled = false;
    fetchWorkspaces().then((rows) => {
      if (!cancelled) setWorkspaces(rows);
    });
    return () => {
      cancelled = true;
    };
  }, [refreshToken]);

  function goToWorkspace(workspace: WorkspaceWithDetails) {
    if (!editor) return;
    ensureWorkspaceShape(editor, workspace, workspace.user_name, workspace.page_slug);
    navigateToWorkspace(editor, workspace, workspace.page_slug);
  }

  return (
    <aside className="attendee-panel" aria-label="Attendees">
      <h2>Attendees</h2>
      {workspaces.length === 0 && <p className="attendee-panel-empty">No one has joined yet.</p>}
      <ul>
        {workspaces.map((workspace) => (
          <li key={workspace.id}>
            <button
              type="button"
              className={
                workspace.user_id === currentUserId ? "attendee attendee-self" : "attendee"
              }
              onClick={() => goToWorkspace(workspace)}
              data-testid={`attendee-${workspace.user_id}`}
            >
              <span className="attendee-name">{workspace.user_name}</span>
              <span className="attendee-page">{workspace.page_title}</span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
