import { Sparkle } from "@phosphor-icons/react";
import { useState } from "react";
import type { Artifact, ModalityGenerationOptions } from "../../data/api";
import { ApiError, runJob } from "../../data/api";
import { usePresenterState } from "../../lib/presenterContext";
import "./GeneratePanel.css";

interface GeneratePanelProps {
  modality: "image" | "video" | "audio";
  options: ModalityGenerationOptions | null;
  onArtifact: (artifact: Artifact) => void;
}

const PLACEHOLDERS: Record<string, string> = {
  image: "a hand-drawn white knight, watercolor edges, plain background",
  video:
    "A medium-wide documentary shot follows an operations lead entering a quiet control room as two warning lights activate on opposite consoles.",
  audio: "a wooden chess piece capturing another, sharp click, short",
};

/** Prompt, model picker, generate. The backend routes each model to its
 * engine; this panel never knows which one answered.
 *
 * Presenter only: generation spends provider budget or the presenter
 * machine's own compute (local audio loads multi-GB models), so
 * attendees get the cached reveals instead of a Generate button. The
 * backend enforces the same rule with a 403. */
export function GeneratePanel({ modality, options, onArtifact }: GeneratePanelProps) {
  const { isPresenter } = usePresenterState();
  const [prompt, setPrompt] = useState("");
  const [modelId, setModelId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const models = options?.models ?? [];
  const firstAvailable = models.find((m) => m.available)?.id ?? null;
  const selected = modelId ?? firstAvailable;
  const ready = options !== null && selected !== null && models.some((m) => m.id === selected);

  async function handleGenerate() {
    if (!ready || !prompt.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await runJob(`${modality}.generate`, {
        prompt: prompt.trim(),
        model: selected,
      });
      onArtifact(response.artifact);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 503) {
        setError("Not configured on the backend. See the model list tooltip.");
      } else {
        setError("Generation failed. Check the backend log.");
      }
    } finally {
      setBusy(false);
    }
  }

  if (!isPresenter) {
    return (
      <div className="generate-panel" data-testid={`generate-panel-${modality}`}>
        <p className="generate-panel-note" data-testid={`generate-presenter-note-${modality}`}>
          Generation is presenter-run: it spends provider budget or the
          presenter machine's compute. The reveals are the room's copies.
        </p>
      </div>
    );
  }

  return (
    <div className="generate-panel" data-testid={`generate-panel-${modality}`}>
      <textarea
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        placeholder={PLACEHOLDERS[modality]}
        rows={2}
        disabled={busy}
      />
      <div className="generate-panel-row">
        <select
          value={selected ?? ""}
          onChange={(event) => setModelId(event.target.value)}
          disabled={busy || models.length === 0}
          title={
            modality === "audio"
              ? "Local models need just install-audio. The fal one needs FAL_KEY."
              : "Runs on fal.ai. Needs FAL_KEY on the backend."
          }
        >
          {models.map((model) => (
            <option key={model.id} value={model.id} disabled={!model.available}>
              {model.label}
              {model.available ? "" : " (not configured)"}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={!ready || busy || !prompt.trim()}
          data-testid={`generate-${modality}`}
        >
          <Sparkle size={12} weight="bold" /> {busy ? "Generating" : "Generate"}
        </button>
      </div>
      {busy && modality === "video" && (
        <p className="generate-panel-note">Video takes a minute or two. Keep talking.</p>
      )}
      {error && <p className="generate-panel-error">{error}</p>}
    </div>
  );
}
