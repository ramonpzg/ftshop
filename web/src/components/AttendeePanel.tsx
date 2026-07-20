import { useEffect, useState } from "react";
import type { Editor } from "tldraw";
import { track } from "tldraw";
import { ensureWorkspaceShape } from "../actions/ensureWorkspaceShape";
import { navigateToWorkspace } from "../actions/navigateToWorkspace";
import { attendeePanelCollapsed, PRESENTATION_PAGE_ID } from "../calculations/attendeePanel";
import { fetchWorkspaces, type WorkspaceWithDetails } from "../data/api";
import "./AttendeePanel.css";

interface AttendeePanelProps {
  editor: Editor | null;
  currentUserId: string | null;
  refreshToken: number;
}

export const AttendeePanel = track(function AttendeePanel({
  editor,
  currentUserId,
  refreshToken,
}: AttendeePanelProps) {
  const [workspaces, setWorkspaces] = useState<WorkspaceWithDetails[]>([]);
  const [expanded, setExpanded] = useState(false);
  const pageId = editor?.getCurrentPageId() ?? null;

  // Leaving the page clears the override, so the next visit to the
  // presentation page starts collapsed again.
  // biome-ignore lint/correctness/useExhaustiveDependencies: pageId is a reset trigger, not read in the body
  useEffect(() => {
    setExpanded(false);
  }, [pageId]);

  // Polls so the presenter can watch the room fill up and late joiners
  // appear without anyone reloading.
  // biome-ignore lint/correctness/useExhaustiveDependencies: refreshToken is a manual refetch trigger, not read in the body
  useEffect(() => {
    let cancelled = false;
    function refresh() {
      fetchWorkspaces()
        .then((rows) => {
          if (!cancelled) setWorkspaces(rows);
        })
        .catch(() => {
          // backend blip; next poll retries
        });
    }
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [refreshToken]);

  function goToWorkspace(workspace: WorkspaceWithDetails) {
    if (!editor) return;
    // Only your own shape is yours to materialize; everyone else's
    // arrives through the sync room when its owner joins.
    if (workspace.user_id === currentUserId) {
      ensureWorkspaceShape(editor, workspace, workspace.user_name, workspace.page_slug);
    }
    navigateToWorkspace(editor, workspace, workspace.page_slug);
  }

  if (attendeePanelCollapsed(pageId, expanded)) {
    return (
      <button
        type="button"
        className="attendee-panel-pill"
        data-testid="attendee-panel-pill"
        onClick={() => setExpanded(true)}
      >
        Attendees ({workspaces.length})
      </button>
    );
  }

  return (
    <aside className="attendee-panel" aria-label="Attendees">
      <div className="attendee-panel-header">
        <h2>Attendees</h2>
        {pageId === PRESENTATION_PAGE_ID && (
          <button
            type="button"
            className="attendee-panel-hide"
            data-testid="attendee-panel-hide"
            onClick={() => setExpanded(false)}
          >
            Hide
          </button>
        )}
      </div>
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
});
