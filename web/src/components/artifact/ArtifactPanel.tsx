import type { Artifact } from "../../data/api";
import "./ArtifactPanel.css";

interface ArtifactPanelProps {
  artifact: Artifact | null;
}

export function ArtifactPanel({ artifact }: ArtifactPanelProps) {
  if (!artifact) {
    return <p className="artifact-panel-empty">Run a job or reveal a cached artifact.</p>;
  }

  const spectrogram = artifact.payload.spectrogram as number[][] | undefined;

  return (
    <div className="artifact-panel" data-testid="artifact-panel">
      <div className="artifact-panel-header">
        <span>{artifact.kind}</span>
        {artifact.cached && <span className="artifact-cached-badge">cached</span>}
      </div>
      {Array.isArray(spectrogram) && <SpectrogramGrid grid={spectrogram} />}
      <pre>{JSON.stringify(artifact.payload, null, 2)}</pre>
    </div>
  );
}

function SpectrogramGrid({ grid }: { grid: number[][] }) {
  const max = Math.max(1e-6, ...grid.flat());
  return (
    <div className="spectrogram-grid" data-testid="spectrogram-grid">
      {grid.map((row, rowIndex) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: grid is a fixed-size, non-reordering matrix
        <div key={rowIndex} className="spectrogram-row">
          {row.map((value, colIndex) => (
            <div
              // biome-ignore lint/suspicious/noArrayIndexKey: grid is a fixed-size, non-reordering matrix
              key={colIndex}
              className="spectrogram-cell"
              style={{ opacity: value / max }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
