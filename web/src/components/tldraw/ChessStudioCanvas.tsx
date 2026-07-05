import type { Editor } from "tldraw";
import { Tldraw } from "tldraw";
import "tldraw/tldraw.css";
import { ensurePagesSeeded } from "../../actions/seedTldrawDocument";
import { PageTabs } from "./PageTabs";
import { ModalityPanelShapeUtil } from "./shapes/ModalityPanelShapeUtil";
import { WorkspaceShapeUtil } from "./shapes/WorkspaceShapeUtil";

const shapeUtils = [WorkspaceShapeUtil, ModalityPanelShapeUtil];

interface ChessStudioCanvasProps {
  onEditorMount?: (editor: Editor) => void;
}

export function ChessStudioCanvas({ onEditorMount }: ChessStudioCanvasProps) {
  return (
    <div className="canvas-area">
      <Tldraw
        persistenceKey="euro-chess-studio"
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
