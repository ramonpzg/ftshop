import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ModalityPanel } from "../../src/components/modality/ModalityPanel";

function routedFetch() {
  let lastArtifact: Record<string, unknown> | null = null;
  return mock(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/artifacts")) {
      return new Response(JSON.stringify(lastArtifact ? [lastArtifact] : []));
    }
    if (url.includes("/evals")) {
      return new Response(
        JSON.stringify([
          {
            id: "eval_1",
            modality: "audio",
            metric: "tag_similarity",
            value: 0.81,
            workspace_id: null,
            source: "cached",
            created_at: "now",
          },
        ]),
      );
    }
    if (url.endsWith("/jobs")) {
      lastArtifact = {
        id: "artifact_1",
        job_config_id: "job_1",
        modality: "audio",
        kind: "spectrogram",
        payload: { spectrogram: [[0.1, 0.2]] },
        cached: false,
        created_at: "now",
      };
      return new Response(
        JSON.stringify({
          job_config: {
            id: "job_1",
            workspace_id: null,
            job_type: "audio.make_spectrogram",
            params_json: "{}",
            created_at: "now",
          },
          artifact: lastArtifact,
        }),
      );
    }
    return new Response("not found", { status: 404 });
  }) as unknown as typeof fetch;
}

afterEach(() => {
  cleanup();
});

describe("ModalityPanel", () => {
  test("shows cached eval results for its modality", async () => {
    globalThis.fetch = routedFetch();
    render(<ModalityPanel modality="audio" isEditing={true} />);

    await waitFor(() => {
      expect(screen.getByText("Tag Similarity")).toBeTruthy();
    });
  });

  test("running a job shows the resulting artifact", async () => {
    globalThis.fetch = routedFetch();
    render(<ModalityPanel modality="audio" isEditing={true} />);

    await waitFor(() => screen.getByTestId("run-job-audio.make_spectrogram"));
    fireEvent.click(screen.getByTestId("run-job-audio.make_spectrogram"));

    await waitFor(() => {
      expect(screen.getByTestId("spectrogram-grid")).toBeTruthy();
    });
  });

  test("shows a hint when not in edit mode", async () => {
    globalThis.fetch = routedFetch();
    render(<ModalityPanel modality="image" isEditing={false} />);
    expect(screen.getByText("Double-click to open")).toBeTruthy();
  });
});
