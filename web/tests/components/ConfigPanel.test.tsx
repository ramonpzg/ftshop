import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ConfigPanel } from "../../src/components/config/ConfigPanel";

afterEach(() => {
  cleanup();
});

describe("ConfigPanel", () => {
  test("renders a button per job", () => {
    render(
      <ConfigPanel
        jobs={[
          { jobType: "text.prompt_eval", label: "Run prompt eval" },
          { jobType: "text.reward_eval", label: "Run reward eval" },
        ]}
        onRunJob={() => {}}
        running={false}
      />,
    );
    expect(screen.getByTestId("run-job-text.prompt_eval")).toBeTruthy();
    expect(screen.getByTestId("run-job-text.reward_eval")).toBeTruthy();
  });

  test("clicking a job button calls onRunJob with its type", () => {
    const onRunJob = mock((_jobType: string) => {});
    render(
      <ConfigPanel
        jobs={[{ jobType: "audio.make_spectrogram", label: "Make spectrogram" }]}
        onRunJob={onRunJob}
        running={false}
      />,
    );
    fireEvent.click(screen.getByTestId("run-job-audio.make_spectrogram"));
    expect(onRunJob).toHaveBeenCalledWith("audio.make_spectrogram");
  });

  test("disables buttons while a job is running", () => {
    render(
      <ConfigPanel
        jobs={[{ jobType: "video.sample_frames", label: "Sample frames" }]}
        onRunJob={() => {}}
        running={true}
      />,
    );
    expect(screen.getByTestId("run-job-video.sample_frames").hasAttribute("disabled")).toBe(true);
  });
});
