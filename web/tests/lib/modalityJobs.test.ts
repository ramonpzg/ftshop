import { describe, expect, test } from "bun:test";
import { jobParams, JOBS_BY_MODALITY } from "../../src/lib/modalityJobs";

describe("JOBS_BY_MODALITY", () => {
  test("has jobs for image, audio, and video", () => {
    expect(JOBS_BY_MODALITY.image.length).toBeGreaterThan(0);
    expect(JOBS_BY_MODALITY.audio.length).toBeGreaterThan(0);
    expect(JOBS_BY_MODALITY.video.length).toBeGreaterThan(0);
  });
});

describe("jobParams", () => {
  test("includes modality and key for reveal-cached jobs", () => {
    expect(jobParams("audio", "artifact.reveal_cached")).toEqual({
      modality: "audio",
      key: "board_sound",
    });
  });

  test("returns empty params for other job types", () => {
    expect(jobParams("image", "image.show_dataset")).toEqual({});
  });
});
