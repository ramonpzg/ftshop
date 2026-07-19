import { getAssetUrlsByImport } from "@tldraw/assets/imports.vite";
import { useSync } from "@tldraw/sync";
import { useEffect, useMemo } from "react";
import type { Editor, TLUser } from "tldraw";
import { atom, defaultBindingUtils, defaultShapeUtils, Tldraw } from "tldraw";
import "tldraw/tldraw.css";
import { registerCanvasPermissions } from "../../actions/registerCanvasPermissions";
import type { CanvasActor } from "../../calculations/canvasOwnership";
import { backendAssetStore } from "../../data/canvasAssets";
import { useCurrentUser } from "../../lib/currentUserContext";
import { usePresenterState } from "../../lib/presenterContext";
import type { RoomStatus } from "../../lib/roomStatus";
import { PageTabs } from "./PageTabs";
import { DeckShapeUtil } from "./shapes/DeckShapeUtil";
import { ModalityPanelShapeUtil } from "./shapes/ModalityPanelShapeUtil";
import { NotebookShapeUtil } from "./shapes/NotebookShapeUtil";
import { WorkspaceShapeUtil } from "./shapes/WorkspaceShapeUtil";

const customShapeUtils = [
  WorkspaceShapeUtil,
  ModalityPanelShapeUtil,
  NotebookShapeUtil,
  DeckShapeUtil,
];

// Fonts, icons, and translations bundled through Vite instead of fetched
// from cdn.tldraw.com at runtime. The app has to work when the venue
// internet does not.
const assetUrls = getAssetUrlsByImport();

interface ChessStudioCanvasProps {
  onEditorMount?: (editor: Editor) => void;
  onRoomStatusChange?: (status: RoomStatus) => void;
}

const PRESENCE_COLORS = ["#e8a33d", "#4f8fde", "#5cb85c", "#c05ccf", "#d9534f", "#3aa8a8"];

function presenceColor(id: string): string {
  let hash = 0;
  for (const char of id) hash = (hash * 31 + char.charCodeAt(0)) % 0xffff;
  return PRESENCE_COLORS[hash % PRESENCE_COLORS.length];
}

/**
 * The shared workshop canvas. The document lives in the sync room (a
 * TLSocketRoom on the workshop host) and every client edits it over a
 * WebSocket at /sync, proxied by the dev server so LAN attendees stay on
 * one origin. Conflicts resolve per record inside tldraw's sync engine;
 * nobody uploads whole-document snapshots anymore, so two browsers can
 * draw at once without one overwriting the other.
 *
 * The connection identifies this client's user and presenter flag in the
 * socket URL. App remounts this component when the user changes, which
 * reconnects with the new identity; until someone joins, the server
 * keeps the session read-only.
 *
 * Ownership rules are enforced locally through store side effects
 * registered on mount; see calculations/canvasOwnership.ts.
 */
export function ChessStudioCanvas({ onEditorMount, onRoomStatusChange }: ChessStudioCanvasProps) {
  const currentUser = useCurrentUser();
  const { isPresenter } = usePresenterState();

  const uri = useMemo(() => {
    const params = new URLSearchParams();
    if (currentUser) params.set("userId", currentUser.id);
    if (isPresenter) params.set("presenter", "1");
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const query = params.toString();
    return `${protocol}://${window.location.host}/sync${query ? `?${query}` : ""}`;
  }, [currentUser, isPresenter]);

  const users = useMemo(() => {
    const name = isPresenter ? "Presenter" : (currentUser?.name ?? "Watching");
    const id = currentUser?.id ?? (isPresenter ? "presenter" : "anonymous");
    const user: TLUser = {
      id: `user:${id}` as TLUser["id"],
      typeName: "user",
      name,
      color: presenceColor(id),
      imageUrl: "",
      meta: {},
    };
    return { currentUser: atom<TLUser | null>("workshop user", user) };
  }, [currentUser, isPresenter]);

  const store = useSync({
    uri,
    assets: backendAssetStore,
    users,
    shapeUtils: useMemo(() => [...defaultShapeUtils, ...customShapeUtils], []),
    bindingUtils: useMemo(() => [...defaultBindingUtils], []),
  });

  const roomStatus: RoomStatus =
    store.status === "loading"
      ? "connecting"
      : store.status === "error"
        ? "error"
        : store.connectionStatus === "offline"
          ? "offline"
          : "live";

  useEffect(() => {
    onRoomStatusChange?.(roomStatus);
  }, [roomStatus, onRoomStatusChange]);

  if (store.status === "error") {
    return (
      <div className="canvas-area canvas-area-message" data-testid="canvas-error">
        Could not reach the room. Check the server, then reload.
      </div>
    );
  }

  return (
    <div className="canvas-area">
      <Tldraw
        store={store}
        shapeUtils={customShapeUtils}
        assetUrls={assetUrls}
        onMount={(editor) => {
          const getActor = (): CanvasActor => ({
            isPresenter,
            userId: currentUser?.id ?? null,
          });
          const dispose = registerCanvasPermissions(editor, getActor);
          onEditorMount?.(editor);
          return dispose;
        }}
        components={{ TopPanel: PageTabs }}
      />
    </div>
  );
}
