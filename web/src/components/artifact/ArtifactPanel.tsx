import { useState } from "react";
import { formatDelta, formatMetricValue, metricLabel } from "../../calculations/formatting";
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

/** A media reference inside a fixture payload: at minimum a file_url,
 * optionally a caption, waveform, poster, or frame strip. */
interface MediaRef {
  label?: string;
  file_url?: string;
  caption?: string;
  waveform_url?: string;
  poster_url?: string;
  frames_url?: string;
  duration_seconds?: number;
}

interface EvidenceMetric {
  metric: string;
  base: number;
  adapted: number;
  delta: number;
  unit?: string;
  direction?: string;
  verdict?: string;
}

function apiUrl(path: unknown): string | null {
  return typeof path === "string" && path.length > 0 ? `/api${path}` : null;
}

function mediaKind(url: string): "image" | "audio" | "video" | "unsupported" {
  const clean = url.split("?")[0].toLowerCase();
  if (/\.(png|jpg|jpeg|gif|webp|svg)$/.test(clean)) return "image";
  if (/\.(wav|mp3|ogg)$/.test(clean)) return "audio";
  if (/\.(mp4|webm)$/.test(clean)) return "video";
  return "unsupported";
}

/** One piece of local media with explicit failure states: a missing
 * file or a playback error reads as words, never as a blank box. */
function MediaFigure({ media, testId }: { media: MediaRef; testId: string }) {
  const [failed, setFailed] = useState(false);
  const url = apiUrl(media.file_url);
  if (!url) {
    return (
      <p className="artifact-media-missing" data-testid={`${testId}-missing`}>
        Media file missing from this artifact.
      </p>
    );
  }
  const kind = mediaKind(url);
  const waveform = apiUrl(media.waveform_url);
  const poster = apiUrl(media.poster_url);
  const frames = apiUrl(media.frames_url);
  return (
    <figure className="artifact-media" data-testid={testId}>
      {media.label && <figcaption className="artifact-media-label">{media.label}</figcaption>}
      {failed ? (
        <p className="artifact-media-failed" data-testid={`${testId}-failed`}>
          {kind === "image"
            ? "Image failed to load."
            : "Playback failed. File missing or unsupported."}
        </p>
      ) : kind === "image" ? (
        <img src={url} alt={media.caption ?? "artifact media"} onError={() => setFailed(true)} />
      ) : kind === "audio" ? (
        <>
          {waveform && <img className="artifact-waveform" src={waveform} alt="waveform" />}
          {/* biome-ignore lint/a11y/useMediaCaption: workshop clips have no caption track */}
          <audio src={url} controls onError={() => setFailed(true)} />
        </>
      ) : kind === "video" ? (
        // biome-ignore lint/a11y/useMediaCaption: workshop clips have no caption track
        <video src={url} poster={poster ?? undefined} controls onError={() => setFailed(true)} />
      ) : (
        <p className="artifact-media-failed" data-testid={`${testId}-unsupported`}>
          Unsupported media type.
        </p>
      )}
      {media.caption && <figcaption>{media.caption}</figcaption>}
      {frames && !failed && (
        <img
          className="artifact-frames-strip"
          src={frames}
          alt="sampled frames"
          data-testid={`${testId}-frames`}
        />
      )}
      {media.duration_seconds !== undefined && (
        <span className="artifact-media-duration">{media.duration_seconds}s</span>
      )}
    </figure>
  );
}

function isMediaRef(value: unknown): value is MediaRef {
  return (
    typeof value === "object" && value !== null && typeof (value as MediaRef).file_url === "string"
  );
}

/** Cached base/adapted metric rows for the modality evidence fixtures.
 * Verdicts are words; a regression is data, not styling. */
function EvidenceMetrics({ metrics }: { metrics: EvidenceMetric[] }) {
  return (
    <table className="artifact-evidence-metrics" data-testid="evidence-metrics">
      <thead>
        <tr>
          <th>Metric</th>
          <th>Base</th>
          <th>Adapted</th>
          <th>Delta</th>
        </tr>
      </thead>
      <tbody>
        {metrics.map((metric) => (
          <tr key={metric.metric}>
            <td>
              {metricLabel(metric.metric)}
              {metric.direction === "lower_is_better" && (
                <span className="artifact-muted"> (lower is better)</span>
              )}
            </td>
            <td>{formatMetricValue(metric.base)}</td>
            <td>{formatMetricValue(metric.adapted)}</td>
            <td>
              {formatDelta(metric.delta)} {metric.verdict}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function ArtifactPanel({ artifact }: ArtifactPanelProps) {
  if (!artifact) {
    return <p className="artifact-panel-empty">Run a job or reveal a cached artifact.</p>;
  }

  const payload = artifact.payload;
  const spectrogram = payload.spectrogram as number[][] | undefined;
  const rows = payload.rows as ImageRow[] | undefined;
  const imageRows = Array.isArray(rows)
    ? rows.filter((row) => pieceImageUrl(row.image) !== null)
    : [];
  const legacyBeforeImage = pieceImageUrl(payload.before_image);
  const fileUrl = apiUrl(payload.file_url);
  const before = isMediaRef(payload.before) ? payload.before : null;
  const after = isMediaRef(payload.after) ? payload.after : null;
  const evidenceMetrics = Array.isArray(payload.metrics)
    ? (payload.metrics as EvidenceMetric[]).filter(
        (metric) => typeof metric?.metric === "string" && typeof metric?.delta === "number",
      )
    : [];
  const chain = payload.chain as
    | Record<string, { label?: string; detail?: string; status?: string }>
    | undefined;
  const framesUrl = apiUrl(payload.frames_url);
  const note = typeof payload.note === "string" ? payload.note : null;
  const resultSource = typeof payload.result_source === "string" ? payload.result_source : null;

  return (
    <div className="artifact-panel" data-testid="artifact-panel">
      <div className="artifact-panel-header">
        <span>{artifact.kind}</span>
        {resultSource && <span className="artifact-cached-badge">{resultSource}</span>}
        {!resultSource && artifact.cached && <span className="artifact-cached-badge">cached</span>}
      </div>
      {fileUrl && artifact.kind === "generated_image" && (
        <img
          className="artifact-generated-image"
          src={fileUrl}
          alt={String(payload.prompt ?? "generated image")}
          data-testid="generated-image"
        />
      )}
      {fileUrl && artifact.kind === "generated_video" && (
        // biome-ignore lint/a11y/useMediaCaption: generated clips have no caption track
        <video
          className="artifact-generated-video"
          src={fileUrl}
          controls
          data-testid="generated-video"
        />
      )}
      {fileUrl && artifact.kind === "generated_audio" && (
        // biome-ignore lint/a11y/useMediaCaption: generated clips have no caption track
        <audio src={fileUrl} controls data-testid="generated-audio" />
      )}
      {fileUrl && !artifact.kind.startsWith("generated_") && (
        <MediaFigure media={payload as unknown as MediaRef} testId="artifact-primary-media" />
      )}
      {framesUrl && (
        <figure className="artifact-media" data-testid="artifact-frames">
          <img src={framesUrl} alt="sampled frames" />
          <figcaption>sampled frames</figcaption>
        </figure>
      )}
      {chain && (
        <ul className="artifact-chain" data-testid="artifact-chain">
          {Object.entries(chain).map(([step, info]) => (
            <li key={step}>
              <span className="artifact-chain-step">{step}</span>
              <span>{[info.label, info.detail ?? info.status].filter(Boolean).join(". ")}</span>
            </li>
          ))}
        </ul>
      )}
      {(before || after) && (
        <div className="artifact-before-after" data-testid="artifact-before-after">
          {before && <MediaFigure media={before} testId="artifact-before" />}
          {after && <MediaFigure media={after} testId="artifact-after" />}
        </div>
      )}
      {evidenceMetrics.length > 0 && <EvidenceMetrics metrics={evidenceMetrics} />}
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
      {legacyBeforeImage && (
        <div className="artifact-image-strip" data-testid="artifact-before-image">
          <figure>
            <img src={legacyBeforeImage} alt="before" />
            <figcaption>before</figcaption>
          </figure>
        </div>
      )}
      {Array.isArray(spectrogram) && <SpectrogramGrid grid={spectrogram} />}
      {note && <p className="artifact-note">{note}</p>}
      <details className="artifact-raw" data-testid="artifact-raw">
        <summary>Raw payload and provenance</summary>
        <pre>{JSON.stringify(payload, null, 2)}</pre>
      </details>
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
