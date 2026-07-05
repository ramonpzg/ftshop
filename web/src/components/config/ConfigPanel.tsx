import "./ConfigPanel.css";

interface JobButton {
  jobType: string;
  label: string;
}

interface ConfigPanelProps {
  jobs: JobButton[];
  onRunJob: (jobType: string) => void;
  running: boolean;
}

export function ConfigPanel({ jobs, onRunJob, running }: ConfigPanelProps) {
  return (
    <div className="config-panel" data-testid="config-panel">
      {jobs.map((job) => (
        <button
          key={job.jobType}
          type="button"
          disabled={running}
          onClick={() => onRunJob(job.jobType)}
          data-testid={`run-job-${job.jobType}`}
        >
          {job.label}
        </button>
      ))}
    </div>
  );
}
