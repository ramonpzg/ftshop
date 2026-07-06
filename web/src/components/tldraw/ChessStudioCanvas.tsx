import { useEffect, useMemo, useState } from "react";
import type { Editor, TLStoreSnapshot } from "tldraw";
import {
  createTLStore,
  defaultBindingUtils,
  defaultShapeUtils,
  getSnapshot,
  loadSnapshot,
  Tldraw,
} from "tldraw";
import "tldraw/tldraw.css";
import { createSaveScheduler, type SaveStatus } from "../../actions/canvasSaveScheduler";
import { ensurePagesSeeded } from "../../actions/seedTldrawDocument";
import { fetchCanvasSnapshot, saveCanvasSnapshot } from "../../data/api";
import { backendAssetStore } from "../../data/canvasAssets";
import { PageTabs } from "./PageTabs";
import { ModalityPanelShapeUtil } from "./shapes/ModalityPanelShapeUtil";
import { WorkspaceShapeUtil } from "./shapes/WorkspaceShapeUtil";

const shapeUtils = [WorkspaceShapeUtil, ModalityPanelShapeUtil];

type CanvasLoadState = "loading" | "ready" | "error";

interface ChessStudioCanvasProps {
  onEditorMount?: (editor: Editor) => void;
  onSaveStatusChange?: (status: SaveStatus) => void;
}

/**
 * The canvas document lives on the backend, not in this browser. On mount
 * the saved snapshot is fetched and loaded; afterwards every document
 * change is saved back, debounced. That is what makes authored slides and
 * assets survive server restarts, browser switches, and serving the app
 * over the venue network.
 *
 * If the snapshot fetch fails the canvas stays read-only-ish: it renders,
 * but saving is disabled so a blank fallback document can never overwrite
 * the real one on the server.
 */
export function ChessStudioCanvas({ onEditorMount, onSaveStatusChange }: ChessStudioCanvasProps) {
  // Unlike the <Tldraw> component, createTLStore does not merge in the
  // default shape and binding utils; without them the schema has no
  // migrations for the built-in shapes and refuses to load.
  const store = useMemo(
    () =>
      createTLStore({
        shapeUtils: [...defaultShapeUtils, ...shapeUtils],
        bindingUtils: defaultBindingUtils,
        assets: backendAssetStore,
      }),
    [],
  );
  const [loadState, setLoadState] = useState<CanvasLoadState>("loading");

  useEffect(() => {
    let cancelled = false;
    fetchCanvasSnapshot()
      .then((snapshot) => {
        if (cancelled) return;
        if (snapshot) {
          loadSnapshot(store, { document: snapshot as unknown as TLStoreSnapshot });
        }
        setLoadState("ready");
      })
      .catch(() => {
        if (!cancelled) setLoadState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [store]);

  useEffect(() => {
    if (loadState !== "ready") return;
    const scheduler = createSaveScheduler({
      getSnapshot: () => getSnapshot(store).document as unknown as Record<string, unknown>,
      save: saveCanvasSnapshot,
      onStatusChange: onSaveStatusChange,
    });
    const unlisten = store.listen(() => scheduler.markDirty(), { scope: "document" });
    const flushOnHide = () => {
      if (document.visibilityState === "hidden") void scheduler.flush();
    };
    document.addEventListener("visibilitychange", flushOnHide);
    return () => {
      document.removeEventListener("visibilitychange", flushOnHide);
      unlisten();
      void scheduler.flush().finally(() => scheduler.dispose());
    };
  }, [store, loadState, onSaveStatusChange]);

  if (loadState === "loading") {
    return (
      <div className="canvas-area canvas-area-message" data-testid="canvas-loading">
        Loading canvas
      </div>
    );
  }

  if (loadState === "error") {
    return (
      <div className="canvas-area canvas-area-message" data-testid="canvas-error">
        Could not load the canvas from the backend. Check the server, then reload.
      </div>
    );
  }

  return (
    <div className="canvas-area">
      <Tldraw
        store={store}
        shapeUtils={shapeUtils}
        onMount={(editor) => {
          ensurePagesSeeded(editor);
          onEditorMount?.(editor);
        }}
        components={{ TopPanel: PageTabs }}
      />
    </div>
  );
}
