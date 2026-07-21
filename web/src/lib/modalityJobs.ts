/** Which jobs are offered on each non-text modality page. */

export interface JobButtonDef {
  jobType: string;
  label: string;
}

export const JOBS_BY_MODALITY: Record<string, JobButtonDef[]> = {
  image: [
    { jobType: "image.show_dataset", label: "Show dataset" },
    { jobType: "artifact.reveal_cached", label: "Reveal cached artifact" },
    { jobType: "image.adaptation_evidence", label: "Show adaptation evidence" },
  ],
  audio: [
    { jobType: "audio.make_spectrogram", label: "Make spectrogram" },
    { jobType: "artifact.reveal_cached", label: "Reveal cached artifact" },
    { jobType: "audio.adaptation_evidence", label: "Show adaptation evidence" },
  ],
  video: [
    { jobType: "video.sample_frames", label: "Sample frames" },
    { jobType: "artifact.reveal_cached", label: "Reveal cached artifact" },
    { jobType: "video.adaptation_evidence", label: "Show adaptation evidence" },
  ],
};

/** Which cached fixture key "Reveal cached artifact" loads for each modality. */
export const REVEAL_CACHED_KEY_BY_MODALITY: Record<string, string> = {
  image: "style_transfer",
  audio: "board_sound",
  video: "chess_moment",
};

export function jobParams(modality: string, jobType: string): Record<string, unknown> {
  if (jobType === "artifact.reveal_cached") {
    return { modality, key: REVEAL_CACHED_KEY_BY_MODALITY[modality] };
  }
  return {};
}
