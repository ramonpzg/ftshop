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

describe("ArtifactPanel media and evidence", () => {
  test("renders a before/after media pair with cached metric verdicts", () => {
    const artifact: Artifact = {
      id: "artifact_1",
      job_config_id: null,
      modality: "image",
      kind: "adaptation_evidence",
      payload: {
        result_source: "cached",
        chain: {
          pairs: { label: "24 (image, caption) pairs" },
          adapter: { label: "wtrclrchess LoRA (illustrative)", status: "not trained live" },
        },
        before: {
          label: "Base output (illustrative)",
          file_url: "/artifacts/media/image/style_before.png",
          caption: "clean bishop",
        },
        after: {
          label: "Adapted output (illustrative)",
          file_url: "/artifacts/media/image/style_after.png",
          caption: "watercolor bishop",
        },
        metrics: [
          {
            metric: "style_consistency",
            base: 0.41,
            adapted: 0.79,
            delta: 0.38,
            direction: "higher_is_better",
            verdict: "improved",
          },
          {
            metric: "piece_identity",
            base: 0.93,
            adapted: 0.88,
            delta: -0.05,
            direction: "higher_is_better",
            verdict: "regressed",
          },
        ],
        note: "Illustrative chain.",
      },
      cached: true,
      created_at: "now",
    };
    render(<ArtifactPanel artifact={artifact} />);
    expect(screen.getByTestId("artifact-before-after")).toBeTruthy();
    expect(screen.getByTestId("artifact-before")).toBeTruthy();
    expect(screen.getByTestId("artifact-after")).toBeTruthy();
    expect(screen.getByTestId("artifact-chain")).toBeTruthy();
    // The trade-off is written out, not styled in.
    expect(screen.getByText(/\+0\.38 improved/)).toBeTruthy();
    expect(screen.getByText(/-0\.05 regressed/)).toBeTruthy();
    // Raw payload stays behind a disclosure.
    expect(screen.getByTestId("artifact-raw")).toBeTruthy();
  });

  test("renders playable audio with its waveform and duration", () => {
    const artifact: Artifact = {
      id: "artifact_1",
      job_config_id: null,
      modality: "audio",
      kind: "board_sound_reveal",
      payload: {
        event: "capture",
        duration_seconds: 0.42,
        file_url: "/artifacts/media/audio/capture_sound.wav",
        waveform_url: "/artifacts/media/audio/capture_sound_waveform.png",
        note: "Synthesized locally.",
      },
      cached: true,
      created_at: "now",
    };
    const { container } = render(<ArtifactPanel artifact={artifact} />);
    expect(screen.getByTestId("artifact-primary-media")).toBeTruthy();
    const audio = container.querySelector("audio");
    expect(audio?.getAttribute("src")).toBe("/api/artifacts/media/audio/capture_sound.wav");
    expect(container.querySelector(".artifact-waveform")).toBeTruthy();
    expect(screen.getByText("0.42s")).toBeTruthy();
  });

  test("renders a video with poster and a frame strip", () => {
    const artifact: Artifact = {
      id: "artifact_1",
      job_config_id: null,
      modality: "video",
      kind: "scenario_video_reveal",
      payload: {
        file_url: "/artifacts/media/video/scene_clip.mp4",
        poster_url: "/artifacts/media/video/scene_poster.png",
        frames_url: "/artifacts/media/video/scene_frames.png",
        duration_seconds: 8.0,
        note: "Storyboard animatic.",
      },
      cached: true,
      created_at: "now",
    };
    const { container } = render(<ArtifactPanel artifact={artifact} />);
    const video = container.querySelector("video");
    expect(video?.getAttribute("src")).toBe("/api/artifacts/media/video/scene_clip.mp4");
    expect(video?.getAttribute("poster")).toBe("/api/artifacts/media/video/scene_poster.png");
    expect(screen.getByTestId("artifact-frames")).toBeTruthy();
  });

  test("a failed image load reads as words, not a blank box", () => {
    const artifact: Artifact = {
      id: "artifact_1",
      job_config_id: null,
      modality: "image",
      kind: "style_transfer_reveal",
      payload: {
        before: { label: "Source render", file_url: "/artifacts/media/image/gone.png" },
      },
      cached: true,
      created_at: "now",
    };
    render(<ArtifactPanel artifact={artifact} />);
    // happy-dom cannot load the file and fires the error event itself,
    // which is exactly the path a missing file takes in a browser.
    expect(screen.getByTestId("artifact-before-failed")).toBeTruthy();
    expect(screen.getByText("Image failed to load.")).toBeTruthy();
  });

  test("an unsupported media extension is called out explicitly", () => {
    const artifact: Artifact = {
      id: "artifact_1",
      job_config_id: null,
      modality: "audio",
      kind: "board_sound_reveal",
      payload: { file_url: "/artifacts/media/audio/capture.flac" },
      cached: true,
      created_at: "now",
    };
    render(<ArtifactPanel artifact={artifact} />);
    expect(screen.getByTestId("artifact-primary-media-unsupported")).toBeTruthy();
  });
});

describe("ArtifactPanel frame evidence", () => {
  test("a media ref's frame strip renders inside its figure", () => {
    const artifact: Artifact = {
      id: "artifact_1",
      job_config_id: null,
      modality: "video",
      kind: "adaptation_evidence",
      payload: {
        after: {
          label: "Adapted take (illustrative)",
          file_url: "/artifacts/media/video/scene_clip.mp4",
          poster_url: "/artifacts/media/video/scene_poster.png",
          frames_url: "/artifacts/media/video/scene_frames.png",
          duration_seconds: 8.0,
        },
      },
      cached: true,
      created_at: "now",
    };
    render(<ArtifactPanel artifact={artifact} />);
    const strip = screen.getByTestId("artifact-after-frames") as HTMLImageElement;
    expect(strip.getAttribute("src")).toBe("/api/artifacts/media/video/scene_frames.png");
  });
});
