import { afterEach, describe, expect, test } from "bun:test";
import { cleanup, render, screen } from "@testing-library/react";
import { ArtifactPanel } from "../../src/components/artifact/ArtifactPanel";
import type { Artifact } from "../../src/data/api";

afterEach(() => {
  cleanup();
});

describe("ArtifactPanel", () => {
  test("shows an empty state with no artifact", () => {
    render(<ArtifactPanel artifact={null} />);
    expect(screen.getByText("Run a job or reveal a cached artifact.")).toBeTruthy();
  });

  test("shows the artifact kind and a cached badge", () => {
    const artifact: Artifact = {
      id: "artifact_1",
      job_config_id: null,
      modality: "image",
      kind: "dataset_sample",
      payload: { rows: [] },
      cached: true,
      created_at: "now",
    };
    render(<ArtifactPanel artifact={artifact} />);
    expect(screen.getByText("dataset_sample")).toBeTruthy();
    expect(screen.getByText("cached")).toBeTruthy();
  });

  test("renders a spectrogram grid when the payload has one", () => {
    const artifact: Artifact = {
      id: "artifact_1",
      job_config_id: null,
      modality: "audio",
      kind: "spectrogram",
      payload: {
        spectrogram: [
          [0.1, 0.2],
          [0.3, 0.4],
        ],
      },
      cached: false,
      created_at: "now",
    };
    render(<ArtifactPanel artifact={artifact} />);
    expect(screen.getByTestId("spectrogram-grid")).toBeTruthy();
  });

  test("does not render a spectrogram grid for other artifact shapes", () => {
    const artifact: Artifact = {
      id: "artifact_1",
      job_config_id: null,
      modality: "video",
      kind: "frame_sample",
      payload: { sampled_indices: [0, 10, 20] },
      cached: false,
      created_at: "now",
    };
    render(<ArtifactPanel artifact={artifact} />);
    expect(screen.queryByTestId("spectrogram-grid")).toBeNull();
  });
});
