import { useEffect, useState } from "react";
import { ArtifactPanel } from "../../components/artifact/ArtifactPanel";
import { ConfigPanel } from "../../components/config/ConfigPanel";
import { EvalPanel } from "../../components/eval/EvalPanel";
import { type Artifact, type EvalResult, fetchArtifacts, fetchEvals, runJob } from "../../data/api";
import { JOBS_BY_MODALITY, jobParams } from "../../lib/modalityJobs";
import "./ModalityPanel.css";

interface ModalityPanelProps {
  modality: string;
  isEditing: boolean;
}

export function ModalityPanel({ modality, isEditing }: ModalityPanelProps) {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [evalResults, setEvalResults] = useState<EvalResult[]>([]);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    refresh();
  }, []);

  function refresh() {
    fetchArtifacts({ modality }).then((artifacts) => setArtifact(artifacts[0] ?? null));
    fetchEvals({ modality }).then(setEvalResults);
  }

  async function handleRunJob(jobType: string) {
    setRunning(true);
    try {
      const response = await runJob(jobType, jobParams(modality, jobType));
      setArtifact(response.artifact);
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
          <h3>Config</h3>
          <ConfigPanel jobs={jobs} onRunJob={handleRunJob} running={running} />
        </section>
        <section className="modality-panel-section">
          <h3>Artifact</h3>
          <ArtifactPanel artifact={artifact} />
        </section>
        <section className="modality-panel-section">
          <h3>Eval</h3>
          <EvalPanel results={evalResults} />
        </section>
      </div>
    </div>
  );
}
