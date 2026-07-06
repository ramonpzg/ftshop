import type { Artifact } from "../../data/api";
import "./ArtifactPanel.css";

interface ArtifactPanelProps {
  artifact: Artifact | null;
}

const PIECE_FILE = /^[wb][KQRBNP]\.svg$/;

function pieceImageUrl(name: unknown): string | null {
  return typeof name === "string" && PIECE_FILE.test(name) ? `/pieces/${name}` : null;
}

interface ImageRow {
  image?: string;
  caption?: string;
}

export function ArtifactPanel({ artifact }: ArtifactPanelProps) {
  if (!artifact) {
    return <p className="artifact-panel-empty">Run a job or reveal a cached artifact.</p>;
  }

  const spectrogram = artifact.payload.spectrogram as number[][] | undefined;
  const rows = artifact.payload.rows as ImageRow[] | undefined;
  const imageRows = Array.isArray(rows)
    ? rows.filter((row) => pieceImageUrl(row.image) !== null)
    : [];
  const beforeImage = pieceImageUrl(artifact.payload.before_image);
  const fileUrl =
    typeof artifact.payload.file_url === "string" ? `/api${artifact.payload.file_url}` : null;

  return (
    <div className="artifact-panel" data-testid="artifact-panel">
      <div className="artifact-panel-header">
        <span>{artifact.kind}</span>
        {artifact.cached && <span className="artifact-cached-badge">cached</span>}
      </div>
      {fileUrl && artifact.kind === "generated_image" && (
        <img
          className="artifact-generated-image"
          src={fileUrl}
          alt={String(artifact.payload.prompt ?? "generated image")}
          data-testid="generated-image"
        />
      )}
      {fileUrl && artifact.kind === "generated_video" && (
        // biome-ignore lint/a11y/useMediaCaption: generated clips have no caption track
        <video className="artifact-generated-video" src={fileUrl} controls data-testid="generated-video" />
      )}
      {fileUrl && artifact.kind === "generated_audio" && (
        // biome-ignore lint/a11y/useMediaCaption: generated clips have no caption track
        <audio src={fileUrl} controls data-testid="generated-audio" />
      )}
      {imageRows.length > 0 && (
        <div className="artifact-image-strip" data-testid="artifact-image-strip">
          {imageRows.map((row) => (
            <figure key={row.image}>
              <img src={pieceImageUrl(row.image) ?? ""} alt={row.caption ?? row.image} />
              <figcaption>{row.caption}</figcaption>
            </figure>
          ))}
        </div>
      )}
      {beforeImage && (
        <div className="artifact-image-strip" data-testid="artifact-before-image">
          <figure>
            <img src={beforeImage} alt="before" />
            <figcaption>before</figcaption>
          </figure>
        </div>
      )}
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
