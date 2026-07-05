import { Tldraw } from "tldraw";
import "tldraw/tldraw.css";
import { ensurePagesSeeded } from "../../actions/seedTldrawDocument";
import { PageTabs } from "./PageTabs";

export function ChessStudioCanvas() {
  return (
    <div className="canvas-area">
      <Tldraw
        persistenceKey="euro-chess-studio"
        onMount={(editor) => {
          ensurePagesSeeded(editor);
        }}
        components={{ TopPanel: PageTabs }}
      />
    </div>
  );
}
