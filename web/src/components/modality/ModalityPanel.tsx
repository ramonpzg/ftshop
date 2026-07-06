import { useCallback, useEffect, useState } from "react";
import { ArtifactPanel } from "../../components/artifact/ArtifactPanel";
import { ConfigPanel } from "../../components/config/ConfigPanel";
import { EvalPanel } from "../../components/eval/EvalPanel";
import {
  type Artifact,
  type EvalResult,
  fetchArtifacts,
  fetchEvals,
  fetchGenerationOptions,
  type GenerationOptions,
  runJob,
} from "../../data/api";
import { JOBS_BY_MODALITY, jobParams } from "../../lib/modalityJobs";
import { GeneratePanel } from "./GeneratePanel";
import "./ModalityPanel.css";

interface ModalityPanelProps {
  modality: string;
  isEditing: boolean;
}

const GENERATIVE_MODALITIES = new Set(["image", "video", "audio"]);

export function ModalityPanel({ modality, isEditing }: ModalityPanelProps) {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [evalResults, setEvalResults] = useState<EvalResult[]>([]);
  const [running, setRunning] = useState(false);
  const [generationOptions, setGenerationOptions] = useState<GenerationOptions | null>(null);

  const refresh = useCallback(() => {
    fetchArtifacts({ modality }).then((artifacts) => setArtifact(artifacts[0] ?? null));
    fetchEvals({ modality }).then(setEvalResults);
  }, [modality]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!GENERATIVE_MODALITIES.has(modality)) return;
    let cancelled = false;
    fetchGenerationOptions()
      .then((options) => {
        if (!cancelled) setGenerationOptions(options);
      })
      .catch(() => {
        if (!cancelled) setGenerationOptions(null);
      });
    return () => {
      cancelled = true;
    };
  }, [modality]);

  async function handleRunJob(jobType: string) {
    setRunning(true);
    try {
      const response = await runJob(jobType, jobParams(modality, jobType));
      setArtifact(response.artifact);
      refresh();
    } finally {
      setRunning(false);
    }
  }

  const jobs = JOBS_BY_MODALITY[modality] ?? [];

  return (
    <div className="modality-panel" data-testid={`modality-panel-${modality}`}>
      <header className="modality-panel-header">
        <span>{modality}</span>
        {!isEditing && <span className="modality-panel-hint">Double-click to open</span>}
      </header>
      <div className="modality-panel-grid">
        <section className="modality-panel-section">
          <h3 title="Run jobs for this modality. The backend decides how each one runs.">Config</h3>
          <ConfigPanel jobs={jobs} onRunJob={handleRunJob} running={running} />
          {GENERATIVE_MODALITIES.has(modality) && (
            <GeneratePanel
              modality={modality as "image" | "video" | "audio"}
              options={
                generationOptions?.[modality as "image" | "video" | "audio"] ?? null
              }
              onArtifact={(generated) => {
                setArtifact(generated);
                refresh();
              }}
            />
          )}
        </section>
        <section className="modality-panel-section">
          <h3 title="Job output lands here: generated files, cached reveals, live calculations.">
            Artifact
          </h3>
          <ArtifactPanel artifact={artifact} />
        </section>
        <section className="modality-panel-section">
          <h3 title="Metrics for this modality. Cached rows need infra the workshop backend does not carry.">
            Eval
          </h3>
          <EvalPanel results={evalResults} />
        </section>
      </div>
    </div>
  );
}
