import { useEffect, useState } from "react";
import type { Editor } from "tldraw";
import type { SaveStatus } from "../actions/canvasSaveScheduler";
import { ensureWorkspaceShape } from "../actions/ensureWorkspaceShape";
import type { JoinResult } from "../actions/joinWorkshop";
import { PRIMARY_WORKSPACE_PAGE_SLUG } from "../actions/joinWorkshop";
import { navigateToWorkspace } from "../actions/navigateToWorkspace";
import { AttendeePanel } from "../components/AttendeePanel";
import { JoinForm } from "../components/JoinForm";
import { PresenterPanel } from "../components/presenter/PresenterPanel";
import { ChessStudioCanvas } from "../components/tldraw/ChessStudioCanvas";
import { SlideControls } from "../components/tldraw/SlideControls";
import { createOrGetWorkspace, fetchHealth } from "../data/api";
import { type LocalUser, loadLocalUser } from "../data/localUser";
import { CurrentUserContext } from "../lib/currentUserContext";
import { PresenterContext } from "../lib/presenterContext";
import "./App.css";

type BackendStatus = "checking" | "connected" | "unreachable";

const SAVE_LABELS: Record<SaveStatus, string> = {
  idle: "",
  saving: "Canvas: saving",
  saved: "Canvas: saved",
  error: "Canvas: save failed",
};

export function App() {
  const [status, setStatus] = useState<BackendStatus>("checking");
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [editor, setEditor] = useState<Editor | null>(null);
  const [currentUser, setCurrentUser] = useState<LocalUser | null>(() => loadLocalUser());
  const [attendeeRefreshToken, setAttendeeRefreshToken] = useState(0);
  const [locked, setLocked] = useState(false);
  const [resetToken, setResetToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then(() => {
        if (!cancelled) setStatus("connected");
      })
      .catch(() => {
        if (!cancelled) setStatus("unreachable");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Re-materializes the returning user's workspace shape once the canvas is
  // ready, covering reloads where tldraw's local store was cleared but the
  // backend still remembers the workspace. Also returns the camera to their
  // workspace, since ensurePagesSeeded always lands a fresh mount on the
  // Presentation page.
  useEffect(() => {
    if (!editor || !currentUser) return;
    let cancelled = false;
    createOrGetWorkspace(currentUser.id, PRIMARY_WORKSPACE_PAGE_SLUG).then((workspace) => {
      if (cancelled) return;
      ensureWorkspaceShape(editor, workspace, currentUser.name, PRIMARY_WORKSPACE_PAGE_SLUG);
      navigateToWorkspace(editor, workspace, PRIMARY_WORKSPACE_PAGE_SLUG);
      setAttendeeRefreshToken((token) => token + 1);
    });
    return () => {
      cancelled = true;
    };
  }, [editor, currentUser]);

  function handleJoined({ user }: JoinResult) {
    setCurrentUser({ id: user.id, name: user.name });
    setAttendeeRefreshToken((token) => token + 1);
  }

  return (
    <CurrentUserContext.Provider value={currentUser}>
      <PresenterContext.Provider value={{ locked, resetToken }}>
        <div className="app-shell">
          <div className="status-badge" data-testid="backend-status">
            Backend: {status}
            {saveStatus !== "idle" && (
              <span data-testid="save-status" data-save-status={saveStatus}>
                {" "}
                | {SAVE_LABELS[saveStatus]}
              </span>
            )}
          </div>
          <ChessStudioCanvas onEditorMount={setEditor} onSaveStatusChange={setSaveStatus} />
          <PresenterPanel
            editor={editor}
            currentUser={currentUser}
            onLockedChange={setLocked}
            onPageReset={() => setResetToken((token) => token + 1)}
          />
          <AttendeePanel
            editor={editor}
            currentUserId={currentUser?.id ?? null}
            refreshToken={attendeeRefreshToken}
          />
          <SlideControls editor={editor} />
          {!currentUser && <JoinForm editor={editor} onJoined={handleJoined} />}
        </div>
      </PresenterContext.Provider>
    </CurrentUserContext.Provider>
  );
}
