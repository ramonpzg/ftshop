import { useEffect, useRef, useState } from "react";
import type { Editor } from "tldraw";
import { ensureWorkspaceShape } from "../actions/ensureWorkspaceShape";
import type { JoinResult } from "../actions/joinWorkshop";
import { PRIMARY_WORKSPACE_PAGE_SLUG } from "../actions/joinWorkshop";
import { navigateToWorkspace } from "../actions/navigateToWorkspace";
import { startPresenterSync } from "../actions/presenterSync";
import { AttendeePanel } from "../components/AttendeePanel";
import { JoinForm } from "../components/JoinForm";
import { PresenterPanel } from "../components/presenter/PresenterPanel";
import { ChessStudioCanvas } from "../components/tldraw/ChessStudioCanvas";
import { SlideControls } from "../components/tldraw/SlideControls";
import { resolveJoinNavigation } from "../actions/joinNavigation";
import { ApiError, createOrGetWorkspace, fetchHealth, fetchRoomHealth } from "../data/api";
import { clearLocalUser, type LocalUser, loadLocalUser } from "../data/localUser";
import { CurrentUserContext } from "../lib/currentUserContext";
import { PresenterContext } from "../lib/presenterContext";
import {
  type CanvasPersistStatus,
  PERSIST_LABELS,
  ROOM_STATUS_LABELS,
  type RoomStatus,
} from "../lib/roomStatus";
import "./App.css";

type BackendStatus = "checking" | "connected" | "unreachable";

// The presenter opens the app with ?presenter=1. This gates the presenter
// panel and exempts that client from remote camera moves and the editing
// lock. It is a v0 convenience, not a security boundary.
function detectPresenter(): boolean {
  return new URLSearchParams(window.location.search).has("presenter");
}

export function App() {
  const [status, setStatus] = useState<BackendStatus>("checking");
  const [roomStatus, setRoomStatus] = useState<RoomStatus>("connecting");
  const [persistStatus, setPersistStatus] = useState<CanvasPersistStatus | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [currentUser, setCurrentUser] = useState<LocalUser | null>(() => loadLocalUser());
  const [attendeeRefreshToken, setAttendeeRefreshToken] = useState(0);
  const [locked, setLocked] = useState(false);
  const [resetToken, setResetToken] = useState(0);
  const [isPresenter] = useState(detectPresenter);
  const [presenterMode, setPresenterMode] = useState("idle");
  const [notice, setNotice] = useState<string | null>(null);
  const currentUserRef = useRef(currentUser);
  currentUserRef.current = currentUser;

  // Concise, transient message when a remote navigation degrades (for
  // example the presenter's frame was deleted).
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), 5000);
    return () => clearTimeout(timer);
  }, [notice]);

  // Deliberate test-and-debug hook: the Playwright suite drives real
  // multi-client scenarios through the live editor.
  useEffect(() => {
    (window as unknown as { chessStudioEditor?: Editor | null }).chessStudioEditor = editor;
  }, [editor]);

  // "Room: live" only says the WebSocket is up. Durability is the sync
  // server's persistence toward the backend disk, polled separately so
  // a dying backend shows up as "save failed, retrying" instead of
  // hiding behind a healthy-looking room.
  useEffect(() => {
    let cancelled = false;
    const poll = () => {
      fetchRoomHealth()
        .then((health) => {
          if (cancelled) return;
          setPersistStatus(health.persist in PERSIST_LABELS ? health.persist : null);
        })
        .catch(() => {
          // Sync server unreachable; the room status badge covers that.
          if (!cancelled) setPersistStatus(null);
        });
    };
    poll();
    const timer = setInterval(poll, 3000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

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
  // ready and returns the camera to it. If the backend no longer knows the
  // remembered user (someone ran just reset-db), drop the stale identity so
  // the join form comes back instead of silently failing on every reload.
  useEffect(() => {
    if (!editor || !currentUser) return;
    let cancelled = false;
    createOrGetWorkspace(currentUser.id, PRIMARY_WORKSPACE_PAGE_SLUG)
      .then(async (workspace) => {
        if (cancelled) return;
        ensureWorkspaceShape(editor, workspace, currentUser.name, PRIMARY_WORKSPACE_PAGE_SLUG);
        setAttendeeRefreshToken((token) => token + 1);
        // Retries until presenter mode is actually known: a transient
        // backend failure must neither move the camera unsafely nor
        // strand an idle-room attendee on the wrong page.
        const navigation = await resolveJoinNavigation({ isCancelled: () => cancelled });
        if (cancelled) return;
        if (navigation === "workspace") {
          navigateToWorkspace(editor, workspace, PRIMARY_WORKSPACE_PAGE_SLUG);
        }
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 404) {
          clearLocalUser();
          setCurrentUser(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [editor, currentUser]);

  // Presenter actions reach every client through this poll loop.
  useEffect(() => {
    if (!editor) return;
    return startPresenterSync({
      editor,
      isPresenter,
      getCurrentUserId: () => currentUserRef.current?.id ?? null,
      onLockedChange: setLocked,
      onStateChange: (state) => setPresenterMode(state.mode),
      onNotice: setNotice,
    });
  }, [editor, isPresenter]);

  function handleJoined({ user }: JoinResult) {
    setCurrentUser({ id: user.id, name: user.name });
    setAttendeeRefreshToken((token) => token + 1);
  }

  return (
    <CurrentUserContext.Provider value={currentUser}>
      <PresenterContext.Provider
        value={{ locked, resetToken, isPresenter, presenterMode, reportNotice: setNotice }}
      >
        <div className="app-shell">
          <div
            className="status-badge"
            data-testid="backend-status"
            data-presenter-mode={presenterMode}
          >
            Backend: {status}
            <span data-testid="room-status" data-room-status={roomStatus}>
              {" "}
              | {ROOM_STATUS_LABELS[roomStatus]}
            </span>
            {persistStatus !== null && (
              <span data-testid="persist-status" data-persist-status={persistStatus}>
                {" "}
                | {PERSIST_LABELS[persistStatus]}
              </span>
            )}
            {notice && (
              <span data-testid="presenter-notice" className="status-notice">
                {" "}
                | {notice}
              </span>
            )}
          </div>
          <ChessStudioCanvas onEditorMount={setEditor} onRoomStatusChange={setRoomStatus} />
          {isPresenter && (
            <PresenterPanel
              editor={editor}
              currentUser={currentUser}
              locked={locked}
              onLockedChange={setLocked}
              onModeChange={setPresenterMode}
              onPageReset={() => setResetToken((token) => token + 1)}
            />
          )}
          <AttendeePanel
            editor={editor}
            currentUserId={currentUser?.id ?? null}
            refreshToken={attendeeRefreshToken}
          />
          <SlideControls editor={editor} />
          {!currentUser && <JoinForm ready={editor !== null} onJoined={handleJoined} />}
        </div>
      </PresenterContext.Provider>
    </CurrentUserContext.Provider>
  );
}
