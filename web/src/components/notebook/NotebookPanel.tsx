import "./NotebookPanel.css";

interface NotebookPanelProps {
  pageSlug: string;
  isEditing: boolean;
}

/** Compatibility view for old canvas snapshots that still contain a
 * notebook-panel shape. New canvases do not seed this shape. */
export function NotebookPanel({ pageSlug, isEditing }: NotebookPanelProps) {
  return (
    <div className="notebook-panel" data-testid={`notebook-panel-${pageSlug}`}>
      <header className="notebook-panel-header">
        <span>Jupyter notebook</span>
        {!isEditing && <span className="notebook-panel-hint">Legacy canvas shape</span>}
      </header>
      <div className="notebook-panel-standalone">
        <span>The notebook runs separately.</span>
        <code>just session-notebook</code>
      </div>
    </div>
  );
}
